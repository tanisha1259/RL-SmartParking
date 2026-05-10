import csv
import json
import pickle
import sys
from pathlib import Path

from q_learning import QLearningAgent


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from sim.parking_env import ParkingEnv

MODELS_DIR = ROOT_DIR / "models"
EXPERIMENTS_DIR = ROOT_DIR / "experiments"
PLOTS_DIR = ROOT_DIR / "plots"


def train(episodes=800):
    env = ParkingEnv(slot_count=12, max_steps=80)
    agent = QLearningAgent(
        actions=range(env.slot_count),
        learning_rate=0.12,
        discount_factor=0.92,
        epsilon=1.0,
        epsilon_min=0.03,
        epsilon_decay=0.992,
    )
    rewards = []
    occupancy_history = []

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
                "episode": episode,
                "avg_occupancy": round(average_occupancy, 3),
                "cars_served": info["cars_served"],
            }
        )

    save_outputs(agent, rewards, occupancy_history)
    print("Training complete.")
    print(f"Policy saved to {MODELS_DIR / 'q_policy.pkl'}")
    print(f"Rewards saved to {EXPERIMENTS_DIR / 'rewards.csv'}")


def save_outputs(agent, rewards, occupancy_history):
    MODELS_DIR.mkdir(exist_ok=True)
    EXPERIMENTS_DIR.mkdir(exist_ok=True)
    PLOTS_DIR.mkdir(exist_ok=True)

    with (MODELS_DIR / "q_policy.pkl").open("wb") as file:
        pickle.dump(agent.export_policy(), file)

    reward_fields = [
        "episode",
        "reward",
        "epsilon",
        "cars_served",
        "rejected_cars",
        "avg_waiting_cars",
        "avg_traffic_level",
        "avg_occupancy",
    ]
    for filename in ["rewards.csv", "training_rewards.csv"]:
        with (EXPERIMENTS_DIR / filename).open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=reward_fields)
            writer.writeheader()
            writer.writerows(rewards)

    with (EXPERIMENTS_DIR / "occupancy.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["episode", "avg_occupancy", "cars_served"])
        writer.writeheader()
        writer.writerows(occupancy_history)

    summary = {
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
    with (EXPERIMENTS_DIR / "training_summary.json").open("w") as file:
        json.dump(summary, file, indent=2)


if __name__ == "__main__":
    train()
