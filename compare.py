import csv
import json
import pickle
import random
from pathlib import Path

from sim.parking_env import ParkingEnv


ROOT_DIR = Path(__file__).resolve().parent
MODELS_DIR = ROOT_DIR / "models"
EXPERIMENTS_DIR = ROOT_DIR / "experiments"


def run_policy(policy, episodes=100):
    env = ParkingEnv()
    rewards = []

    for _ in range(episodes):
        state = env.reset()
        done = False
        total_reward = 0

        while not done:
            valid_actions = env.available_actions()
            action_values = policy.get(state, {})
            action = choose_best_valid_action(action_values, valid_actions)
            state, reward, done, _ = env.step(action)
            total_reward += reward

        rewards.append(total_reward)

    return rewards


def run_baseline(episodes=100):
    env = ParkingEnv()
    rewards = []

    for _ in range(episodes):
        state = env.reset()
        done = False
        total_reward = 0

        while not done:
            valid_actions = env.available_actions()
            action = random.choice(valid_actions) if valid_actions else None
            state, reward, done, _ = env.step(action)
            total_reward += reward

        rewards.append(total_reward)

    return rewards


def choose_best_valid_action(action_values, valid_actions):
    if not valid_actions:
        return None
    if not action_values:
        return random.choice(valid_actions)
    return max(valid_actions, key=lambda action: action_values.get(action, 0))


def main():
    policy_path = MODELS_DIR / "q_policy.pkl"
    if not policy_path.exists():
        raise FileNotFoundError("Train the RL agent first: python rl/train.py")

    with policy_path.open("rb") as file:
        policy = pickle.load(file)

    rl_rewards = run_policy(policy)
    baseline_rewards = run_baseline()
    summary = {
        "rl_average_reward": round(sum(rl_rewards) / len(rl_rewards), 2),
        "baseline_average_reward": round(
            sum(baseline_rewards) / len(baseline_rewards),
            2,
        ),
        "episodes": len(rl_rewards),
    }

    EXPERIMENTS_DIR.mkdir(exist_ok=True)
    with (EXPERIMENTS_DIR / "evaluation_summary.json").open("w") as file:
        json.dump(summary, file, indent=2)

    with (EXPERIMENTS_DIR / "comparison_rewards.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["episode", "rl", "baseline"])
        writer.writeheader()
        for index, (rl_reward, baseline_reward) in enumerate(
            zip(rl_rewards, baseline_rewards),
            start=1,
        ):
            writer.writerow(
                {"episode": index, "rl": rl_reward, "baseline": baseline_reward}
            )

    print(summary)


if __name__ == "__main__":
    main()
