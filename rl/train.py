import argparse
import csv
import json
import pickle
import sys
import uuid
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from rl.config import load_qlearning_config
from rl.experiment_tracking import ExperimentResult, append_experiment_result
from rl.logging_config import configure_training_logger
from rl.q_learning import QLearningAgent
from sim.parking_env import ParkingEnv

MODELS_DIR = ROOT_DIR / "models"
EXPERIMENTS_DIR = ROOT_DIR / "experiments"
PLOTS_DIR = ROOT_DIR / "plots"
LOGS_DIR = ROOT_DIR / "logs"
RESULTS_PATH = EXPERIMENTS_DIR / "results.csv"
TRAINING_LOG_PATH = LOGS_DIR / "training.log"


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
    
    train(args.config)
