import argparse
import csv
import json
import pickle
import sys
import uuid
import yaml
from pathlib import Path

from q_learning import QLearningAgent

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from sim.parking_env import ParkingEnv

MODELS_DIR = ROOT_DIR / "models"
EXPERIMENTS_DIR = ROOT_DIR / "experiments"
PLOTS_DIR = ROOT_DIR / "plots"


def train(config_path):
    # Load configuration
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    episodes = config.get("episodes", 800)
    run_id = f"run_{uuid.uuid4().hex[:8]}"

    env = ParkingEnv(slot_count=12, max_steps=80)
    agent = QLearningAgent(
        actions=range(env.slot_count),
        learning_rate=config.get("learning_rate", 0.12),
        discount_factor=config.get("discount_factor", 0.92),
        epsilon=config.get("epsilon_start", 1.0),
        epsilon_min=config.get("epsilon_min", 0.03),
        epsilon_decay=config.get("epsilon_decay", 0.992),
    )
    
    rewards = []
    occupancy_history = []

    print(f"Starting training run: {run_id}")
    print(f"Config: {config}")

    for episode in range(1, episodes + 1):
        state = env.reset()
        total_reward = 0
        occupancy_total = 0
        waiting_total = 0
        traffic_total = 0
        done = False

        while not done:
            valid_actions = env.available_actions()
            action = agent.choose_action(state, valid_actions)
            next_state, reward, done, info = env.step(action)
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
        occupancy_history.append(
            {
                "run_id": run_id,
                "episode": episode,
                "avg_occupancy": round(average_occupancy, 3),
                "cars_served": info["cars_served"],
            }
        )

    model_name = config.get("model_name", "q_policy.pkl")
    save_outputs(agent, rewards, occupancy_history, run_id, config, model_name)
    print("Training complete.")
    print(f"Policy saved to {MODELS_DIR / model_name}")
    print(f"Rewards saved to {EXPERIMENTS_DIR / f'rewards_{run_id}.csv'}")


def save_outputs(agent, rewards, occupancy_history, run_id, config, model_name):
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
        "config_used": config,
        "episodes": len(rewards),
        "final_epsilon": rewards[-1]["epsilon"],
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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train RL agent for Smart Parking")
    parser.add_argument(
        "--config", 
        type=str, 
        default=str(ROOT_DIR / "configs" / "qlearning_v1.yaml"),
        help="Path to the YAML configuration file"
    )
    args = parser.parse_args()
    
    train(args.config)
