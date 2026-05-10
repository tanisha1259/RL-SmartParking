import csv
from pathlib import Path

import matplotlib.pyplot as plt


ROOT_DIR = Path(__file__).resolve().parent
EXPERIMENTS_DIR = ROOT_DIR / "experiments"
PLOTS_DIR = ROOT_DIR / "plots"


def plot_training_rewards():
    rewards_path = EXPERIMENTS_DIR / "training_rewards.csv"
    if not rewards_path.exists():
        raise FileNotFoundError("Train first: python rl/train.py")

    episodes = []
    rewards = []

    with rewards_path.open() as file:
        reader = csv.DictReader(file)
        for row in reader:
            episodes.append(int(row["episode"]))
            rewards.append(float(row["reward"]))

    PLOTS_DIR.mkdir(exist_ok=True)
    plt.figure(figsize=(10, 5))
    plt.plot(episodes, rewards)
    plt.title("Q-learning Training Rewards")
    plt.xlabel("Episode")
    plt.ylabel("Reward")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "training_rewards.png")
    print(f"Plot saved to {PLOTS_DIR / 'training_rewards.png'}")


if __name__ == "__main__":
    plot_training_rewards()
