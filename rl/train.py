import argparse
import csv
import json
import pickle
import random
import sys
import uuid
from pathlib import Path

import numpy as np
import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from rl.config import load_qlearning_config
from rl.dqn_model import DQNModel
from rl.experiment_tracking import ExperimentResult, append_experiment_result
from rl.logging_config import configure_training_logger
from rl.q_learning import QLearningAgent
from rl.replay_buffer import ReplayBuffer
from sim.parking_env import ParkingEnv

MODELS_DIR = ROOT_DIR / "models"
EXPERIMENTS_DIR = ROOT_DIR / "experiments"
PLOTS_DIR = ROOT_DIR / "plots"
LOGS_DIR = ROOT_DIR / "logs"
RESULTS_PATH = EXPERIMENTS_DIR / "results.csv"
TRAINING_LOG_PATH = LOGS_DIR / "training.log"


def train_from_config(config_path):
    with Path(config_path).open("r", encoding="utf-8") as file:
        raw_config = yaml.safe_load(file) or {}

    if raw_config.get("algorithm", "qlearning") == "dqn":
        train_dqn(config_path, raw_config)
    else:
        train(config_path)


def train(config_path):
    config = load_qlearning_config(config_path)
    logger = configure_training_logger(TRAINING_LOG_PATH)

    run_id = f"run_{uuid.uuid4().hex[:8]}"

    env = ParkingEnv(**config.environment.as_kwargs())
    agent = QLearningAgent(
        actions=range(env.slot_count),
        learning_rate=config.agent.learning_rate,
        discount_factor=config.agent.discount_factor,
        epsilon=config.agent.epsilon_start,
        epsilon_min=config.agent.epsilon_min,
        epsilon_decay=config.agent.epsilon_decay,
    )

    rewards = []
    occupancy_history = []
    wait_times = []

    logger.info("Starting training run | run_id=%s | config=%s", run_id, config.raw)

    for episode in range(1, config.training.episodes + 1):
        state = env.reset()
        total_reward = 0
        occupancy_total = 0
        waiting_total = 0
        traffic_total = 0
        step = 0
        done = False

        while not done:
            step += 1
            valid_actions = env.available_actions()
            action = agent.choose_action(state, valid_actions)
            cars_served_before_step = env.cars_served
            next_state, reward, done, info = env.step(action)
            allocation_success = info["cars_served"] > cars_served_before_step
            _log_allocation_step(
                logger=logger,
                run_id=run_id,
                episode=episode,
                step=step,
                action=action,
                reward=reward,
                epsilon=agent.epsilon,
                allocation_success=allocation_success,
            )
            next_valid_actions = env.available_actions()
            agent.learn(state, action, reward, next_state, done, next_valid_actions)
            state = next_state
            total_reward += reward
            occupancy_total += info["occupancy_rate"]
            waiting_total += info["waiting_cars"]
            traffic_total += info["traffic_level"]

        agent.decay_epsilon()
        average_occupancy = occupancy_total / env.max_steps
        average_waiting = waiting_total / env.max_steps
        average_traffic = traffic_total / env.max_steps
        wait_times.append(info["average_wait"])
        
        rewards.append(
            {
                "run_id": run_id,
                "episode": episode,
                "reward": round(total_reward, 3),
                "epsilon": round(agent.epsilon, 4),
                "cars_served": info["cars_served"],
                "rejected_cars": info["rejected_cars"],
                "avg_waiting_cars": round(average_waiting, 3),
                "avg_traffic_level": round(average_traffic, 3),
                "avg_occupancy": round(average_occupancy, 3),
            }
        )
        logger.info(
            "Episode complete | run_id=%s | episode=%s | reward=%.3f | epsilon=%.4f",
            run_id,
            episode,
            total_reward,
            agent.epsilon,
        )
        occupancy_history.append(
            {
                "run_id": run_id,
                "episode": episode,
                "avg_occupancy": round(average_occupancy, 3),
                "cars_served": info["cars_served"],
            }
        )

    model_name = config.training.model_name
    save_outputs(
        agent,
        rewards,
        occupancy_history,
        wait_times,
        run_id,
        config,
        model_name,
    )
    logger.info("Training complete | run_id=%s", run_id)
    logger.info("Policy saved | path=%s", MODELS_DIR / model_name)
    logger.info("Rewards saved | path=%s", EXPERIMENTS_DIR / f"rewards_{run_id}.csv")
    logger.info("Experiment result appended | path=%s", RESULTS_PATH)


def train_dqn(config_path, raw_config=None):
    raw_config = raw_config or _load_raw_config(config_path)
    logger = configure_training_logger(TRAINING_LOG_PATH)
    run_id = f"dqn_{uuid.uuid4().hex[:8]}"

    seed = raw_config.get("seed", 42)
    random.seed(seed)
    np.random.seed(seed)

    env_config = raw_config["environment"]
    training_config = raw_config["training"]
    agent_config = raw_config["agent"]

    env = ParkingEnv(**env_config)
    input_size = (env.slot_count * 2) + 5
    output_size = env.slot_count
    online_model = DQNModel(
        input_size=input_size,
        output_size=output_size,
        hidden_sizes=tuple(agent_config.get("hidden_sizes", [128, 64])),
        seed=seed,
    )
    target_model = DQNModel(
        input_size=input_size,
        output_size=output_size,
        hidden_sizes=tuple(agent_config.get("hidden_sizes", [128, 64])),
        seed=seed + 1,
    )
    target_model.copy_from(online_model)
    replay = ReplayBuffer(agent_config.get("replay_capacity", 2000), seed=seed)

    epsilon = agent_config["epsilon_start"]
    rewards = []
    losses = []
    occupancy_history = []
    wait_times = []

    logger.info("Starting DQN training run | run_id=%s | config=%s", run_id, raw_config)

    for episode in range(1, training_config["episodes"] + 1):
        state = env.reset()
        state_vector = _encode_dqn_state(state, env)
        total_reward = 0.0
        occupancy_total = 0.0
        waiting_total = 0.0
        traffic_total = 0.0
        distance_total = 0.0
        final_info = {}
        done = False

        while not done:
            valid_actions = env.available_actions()
            action = _choose_dqn_action(online_model, state_vector, valid_actions, epsilon)
            next_state, reward, done, final_info = env.step(action)
            next_vector = _encode_dqn_state(next_state, env)
            next_valid_actions = env.available_actions()
            replay.push(state_vector, action, reward, next_vector, done, next_valid_actions)

            if len(replay) >= agent_config["batch_size"]:
                loss = _learn_from_replay(
                    replay,
                    online_model,
                    target_model,
                    agent_config["batch_size"],
                    agent_config["learning_rate"],
                    agent_config["gamma"],
                )
                losses.append(loss)

            state_vector = next_vector
            total_reward += reward
            occupancy_total += final_info["occupancy_rate"]
            waiting_total += final_info["waiting_cars"]
            traffic_total += final_info["traffic_level"]
            distance_total += _normalized_distance(action, env.slot_count)

        if episode % agent_config.get("target_update_interval", 10) == 0:
            target_model.copy_from(online_model)

        epsilon = max(agent_config["epsilon_min"], epsilon * agent_config["epsilon_decay"])
        average_occupancy = occupancy_total / env.max_steps
        average_waiting = waiting_total / env.max_steps
        average_traffic = traffic_total / env.max_steps
        average_distance = distance_total / env.max_steps
        wait_times.append(final_info["average_wait"])

        rewards.append(
            {
                "run_id": run_id,
                "episode": episode,
                "reward": round(total_reward, 3),
                "epsilon": round(epsilon, 4),
                "cars_served": final_info["cars_served"],
                "rejected_cars": final_info["rejected_cars"],
                "avg_waiting_cars": round(average_waiting, 3),
                "avg_traffic_level": round(average_traffic, 3),
                "avg_occupancy": round(average_occupancy, 3),
                "avg_distance": round(average_distance, 3),
                "loss": round(_average(losses[-20:]), 5),
            }
        )
        occupancy_history.append(
            {
                "run_id": run_id,
                "episode": episode,
                "avg_occupancy": round(average_occupancy, 3),
                "cars_served": final_info["cars_served"],
            }
        )

        logger.info(
            "DQN episode complete | run_id=%s | episode=%s | reward=%.3f | epsilon=%.4f",
            run_id,
            episode,
            total_reward,
            epsilon,
        )

    save_dqn_outputs(
        online_model,
        rewards,
        occupancy_history,
        wait_times,
        run_id,
        raw_config,
        epsilon,
    )
    logger.info("DQN training complete | run_id=%s", run_id)


def save_dqn_outputs(model, rewards, occupancy_history, wait_times, run_id, config, epsilon):
    MODELS_DIR.mkdir(exist_ok=True)
    EXPERIMENTS_DIR.mkdir(exist_ok=True)
    PLOTS_DIR.mkdir(exist_ok=True)

    metadata = {
        "run_id": run_id,
        "algorithm": "dqn",
        "epsilon": epsilon,
        "config": config,
    }
    policy = model.export_policy(metadata)
    model_names = [
        config["training"].get("model_name", "policy_v1.pkl"),
        config["training"].get("shadow_model_name", "policy_v2.pkl"),
    ]
    for model_name in dict.fromkeys(model_names):
        with (MODELS_DIR / model_name).open("wb") as file:
            pickle.dump(policy, file)

    reward_fields = [
        "run_id",
        "episode",
        "reward",
        "epsilon",
        "cars_served",
        "rejected_cars",
        "avg_waiting_cars",
        "avg_traffic_level",
        "avg_occupancy",
        "avg_distance",
        "loss",
    ]
    with (EXPERIMENTS_DIR / f"rewards_{run_id}.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=reward_fields)
        writer.writeheader()
        writer.writerows(rewards)

    master_csv_path = EXPERIMENTS_DIR / "master_rewards.csv"
    should_write_header = not master_csv_path.exists() or master_csv_path.stat().st_size == 0
    with master_csv_path.open("a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=reward_fields)
        if should_write_header:
            writer.writeheader()
        writer.writerows(rewards)

    with (EXPERIMENTS_DIR / f"occupancy_{run_id}.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["run_id", "episode", "avg_occupancy", "cars_served"])
        writer.writeheader()
        writer.writerows(occupancy_history)

    summary = {
        "run_id": run_id,
        "algorithm": "dqn",
        "episodes": len(rewards),
        "epsilon": round(epsilon, 4),
        "learning_rate": config["agent"]["learning_rate"],
        "gamma": config["agent"]["gamma"],
        "average_reward": round(_average(row["reward"] for row in rewards), 3),
        "congestion_score": round(_average(row["avg_traffic_level"] for row in rewards), 3),
        "average_distance": round(_average(row["avg_distance"] for row in rewards), 3),
        "throughput": round(_average(row["cars_served"] for row in rewards), 3),
        "average_wait_time": round(_average(wait_times), 3),
        "models": model_names,
    }
    with (EXPERIMENTS_DIR / f"training_summary_{run_id}.json").open("w") as file:
        json.dump(summary, file, indent=2)

    log_path = EXPERIMENTS_DIR / "log.json"
    existing_log = []
    if log_path.exists() and log_path.stat().st_size:
        with log_path.open("r", encoding="utf-8") as file:
            existing_log = json.load(file)
    existing_log.append(summary)
    with log_path.open("w", encoding="utf-8") as file:
        json.dump(existing_log, file, indent=2)

    append_experiment_result(
        RESULTS_PATH,
        ExperimentResult(
            run_id=run_id,
            episodes=len(rewards),
            epsilon=epsilon,
            learning_rate=config["agent"]["learning_rate"],
            gamma=config["agent"]["gamma"],
            average_reward=summary["average_reward"],
            congestion_score=summary["congestion_score"],
            average_distance=summary["average_distance"],
            throughput=summary["throughput"],
            average_wait_time=summary["average_wait_time"],
        ),
    )


def save_outputs(agent, rewards, occupancy_history, wait_times, run_id, config, model_name):
    MODELS_DIR.mkdir(exist_ok=True)
    EXPERIMENTS_DIR.mkdir(exist_ok=True)
    PLOTS_DIR.mkdir(exist_ok=True)

    with (MODELS_DIR / model_name).open("wb") as file:
        pickle.dump(agent.export_policy(), file)

    reward_fields = [
        "run_id",
        "episode",
        "reward",
        "epsilon",
        "cars_served",
        "rejected_cars",
        "avg_waiting_cars",
        "avg_traffic_level",
        "avg_occupancy",
    ]
    
    # Save a run-specific CSV to track this exact experiment
    with (EXPERIMENTS_DIR / f"rewards_{run_id}.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=reward_fields)
        writer.writeheader()
        writer.writerows(rewards)

    # Append to a master CSV for overall tracking (optional but good for MLOps)
    master_csv_path = EXPERIMENTS_DIR / "master_rewards.csv"
    file_exists = master_csv_path.exists()
    with master_csv_path.open("a", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=reward_fields)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rewards)

    with (EXPERIMENTS_DIR / f"occupancy_{run_id}.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["run_id", "episode", "avg_occupancy", "cars_served"])
        writer.writeheader()
        writer.writerows(occupancy_history)

    summary = {
        "run_id": run_id,
        "config_used": config.raw,
        "episodes": len(rewards),
        "final_epsilon": rewards[-1]["epsilon"],
        "average_reward": round(_average(row["reward"] for row in rewards), 3),
        "average_wait_time": round(_average(wait_times), 3),
        "average_reward_last_50": round(
            sum(row["reward"] for row in rewards[-50:]) / min(50, len(rewards)),
            3,
        ),
        "average_occupancy_last_50": round(
            sum(row["avg_occupancy"] for row in rewards[-50:]) / min(50, len(rewards)),
            3,
        ),
    }
    with (EXPERIMENTS_DIR / f"training_summary_{run_id}.json").open("w") as file:
        json.dump(summary, file, indent=2)

    append_experiment_result(
        RESULTS_PATH,
        ExperimentResult(
            run_id=run_id,
            episodes=len(rewards),
            epsilon=agent.epsilon,
            learning_rate=config.agent.learning_rate,
            gamma=config.agent.discount_factor,
            average_reward=summary["average_reward"],
            average_wait_time=summary["average_wait_time"],
        ),
    )


def _average(values):
    values = list(values)
    return sum(values) / len(values) if values else 0


def _load_raw_config(config_path):
    with Path(config_path).open("r", encoding="utf-8") as file:
        return yaml.safe_load(file) or {}


def _encode_dqn_state(state, env):
    occupancy = list(state[: env.slot_count])
    waiting_bucket = state[-2] / 3
    traffic_bucket = state[-1] / 3
    zone_size = max(1, env.slot_count // 3)
    zone_congestion = []
    for start in range(0, env.slot_count, zone_size):
        zone = occupancy[start : start + zone_size]
        if len(zone_congestion) == 3:
            break
        zone_congestion.append(sum(zone) / max(1, len(zone)))
    while len(zone_congestion) < 3:
        zone_congestion.append(0)
    availability = [1 - value for value in occupancy]
    return np.asarray(occupancy + zone_congestion + [waiting_bucket, traffic_bucket] + availability, dtype=float)


def _choose_dqn_action(model, state_vector, valid_actions, epsilon):
    if not valid_actions:
        return None
    if random.random() < epsilon:
        return random.choice(valid_actions)
    q_values = model.predict(state_vector)
    return max(valid_actions, key=lambda action: q_values[action])


def _learn_from_replay(replay, online_model, target_model, batch_size, learning_rate, gamma):
    batch = replay.sample(batch_size)
    states = []
    target_rows = []
    for state, action, reward, next_state, done, valid_actions in batch:
        current_q = online_model.predict(state)
        target_q = current_q.copy()
        if action is not None:
            if done or not valid_actions:
                target_value = reward
            else:
                next_q = target_model.predict(next_state)
                target_value = reward + gamma * max(next_q[next_action] for next_action in valid_actions)
            target_q[action] = target_value
        states.append(state)
        target_rows.append(target_q)
    return online_model.train_step(states, target_rows, learning_rate)


def _normalized_distance(action, slot_count):
    if action is None:
        return 1.0
    return action / max(1, slot_count - 1)


def _log_allocation_step(
    logger,
    run_id,
    episode,
    step,
    action,
    reward,
    epsilon,
    allocation_success,
):
    slot = "none" if action is None else action
    status = "success" if allocation_success else "failure"
    logger.info(
        "Allocation step | run_id=%s | episode=%s | step=%s | slot=%s | status=%s | reward=%.3f | epsilon=%.4f",
        run_id,
        episode,
        step,
        slot,
        status,
        reward,
        epsilon,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train RL agent for Smart Parking")
    parser.add_argument(
        "--config", 
        type=str, 
        default=str(ROOT_DIR / "configs" / "qlearning.yaml"),
        help="Path to the YAML configuration file"
    )
    args = parser.parse_args()
    
    train_from_config(args.config)
