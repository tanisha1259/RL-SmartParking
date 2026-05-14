import csv
from pathlib import Path

import matplotlib.pyplot as plt


ROOT_DIR = Path(__file__).resolve().parent
EXPERIMENTS_DIR = ROOT_DIR / "experiments"
PLOTS_DIR = ROOT_DIR / "plots"


def plot_training_rewards():
    rewards_path = EXPERIMENTS_DIR / "master_rewards.csv"
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
    plt.title("Reward vs Episode")
    plt.xlabel("Episode")
    plt.ylabel("Reward")
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "reward_vs_episode.png")
    print(f"Plot saved to {PLOTS_DIR / 'reward_vs_episode.png'}")


def plot_training_metric(column, output_name, title, ylabel, color):
    rewards_path = EXPERIMENTS_DIR / "master_rewards.csv"
    if not rewards_path.exists():
        raise FileNotFoundError("Train first: python rl/train.py")

    episodes = []
    values = []
    with rewards_path.open() as file:
        reader = csv.DictReader(file)
        for row in reader:
            if column not in row or row[column] in ("", None):
                continue
            episodes.append(int(row["episode"]))
            values.append(float(row[column]))

    if not values:
        return

    PLOTS_DIR.mkdir(exist_ok=True)
    plt.figure(figsize=(10, 5))
    plt.plot(episodes, values, color=color)
    plt.title(title)
    plt.xlabel("Episode")
    plt.ylabel(ylabel)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / output_name)
    print(f"Plot saved to {PLOTS_DIR / output_name}")


def plot_occupancy():
    occupancy_files = list(EXPERIMENTS_DIR.glob("occupancy_*.csv"))
    if not occupancy_files:
        raise FileNotFoundError("Train first: python rl/train.py")
    occupancy_path = occupancy_files[0]

    episodes = []
    occupancy = []

    with occupancy_path.open() as file:
        reader = csv.DictReader(file)
        for row in reader:
            episodes.append(int(row["episode"]))
            occupancy.append(float(row["avg_occupancy"]))

    PLOTS_DIR.mkdir(exist_ok=True)
    plt.figure(figsize=(10, 5))
    plt.plot(episodes, occupancy, color="#2f855a")
    plt.title("Average Parking Occupancy During Training")
    plt.xlabel("Episode")
    plt.ylabel("Average occupancy")
    plt.ylim(0, 1)
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "occupancy_vs_time.png")
    print(f"Plot saved to {PLOTS_DIR / 'occupancy_vs_time.png'}")


def plot_comparison():
    comparison_path = EXPERIMENTS_DIR / "comparison_rewards.csv"
    if not comparison_path.exists():
        raise FileNotFoundError("Evaluate first: python compare.py")

    episodes = []
    rl_rewards = []
    baseline_rewards = []
    rl_occupancy = []
    baseline_occupancy = []

    with comparison_path.open() as file:
        reader = csv.DictReader(file)
        for row in reader:
            episodes.append(int(row["episode"]))
            rl_rewards.append(float(row["rl_reward"]))
            baseline_rewards.append(float(row["baseline_reward"]))
            rl_occupancy.append(float(row["rl_occupancy"]))
            baseline_occupancy.append(float(row["baseline_occupancy"]))

    PLOTS_DIR.mkdir(exist_ok=True)
    plt.figure(figsize=(10, 5))
    plt.plot(episodes, rl_rewards, label="RL policy")
    plt.plot(episodes, baseline_rewards, label="Nearest-slot baseline", alpha=0.8)
    plt.title("RL vs Baseline Rewards")
    plt.xlabel("Episode")
    plt.ylabel("Reward")
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "rl_vs_baseline_rewards.png")
    print(f"Plot saved to {PLOTS_DIR / 'rl_vs_baseline_rewards.png'}")

    plt.figure(figsize=(10, 5))
    plt.plot(episodes, rl_occupancy, label="RL policy", color="#2f855a")
    plt.plot(
        episodes,
        baseline_occupancy,
        label="Nearest-slot baseline",
        color="#805ad5",
        alpha=0.8,
    )
    plt.title("RL vs Baseline Occupancy")
    plt.xlabel("Episode")
    plt.ylabel("Occupancy")
    plt.ylim(0, 1)
    plt.legend()
    plt.tight_layout()
    plt.savefig(PLOTS_DIR / "rl_vs_baseline_occupancy.png")
    print(f"Plot saved to {PLOTS_DIR / 'rl_vs_baseline_occupancy.png'}")


if __name__ == "__main__":
    plot_training_rewards()
    plot_training_metric(
        "avg_traffic_level",
        "congestion_vs_time.png",
        "Congestion vs Time",
        "Average traffic level",
        "#b7605d",
    )
    plot_training_metric(
        "cars_served",
        "throughput_vs_time.png",
        "Throughput vs Time",
        "Cars served",
        "#4aa3a2",
    )
    plot_occupancy()
    try:
        plot_comparison()
    except FileNotFoundError as error:
        print(error)
