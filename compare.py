import csv
import json
import pickle
import random
import statistics
from pathlib import Path

from rl.dqn_model import DQNModel
from sim.parking_env import ParkingEnv

ROOT_DIR = Path(__file__).resolve().parent
MODELS_DIR = ROOT_DIR / "models"
EXPERIMENTS_DIR = ROOT_DIR / "experiments"


def load_q_table(policy_path):
    with policy_path.open("rb") as file:
        policy = pickle.load(file)
    if isinstance(policy, dict) and policy.get("type") == "dqn_numpy":
        return policy
    if isinstance(policy, dict) and "q_table" in policy:
        return policy["q_table"]
    return policy


def run_policy(policy, episodes=150):
    env = ParkingEnv(**policy_environment_kwargs(policy))
    results = []

    for _ in range(episodes):
        state = env.reset()
        done = False
        total_reward = 0
        distance_total = 0
        steps = 0
        final_info = {}

        while not done:
            steps += 1
            valid_actions = env.available_actions()
            action = choose_policy_action(policy, state, env, valid_actions)
            state, reward, done, final_info = env.step(action)
            total_reward += reward
            distance_total += normalized_distance(action, env.slot_count)

        results.append(_episode_result(total_reward, final_info, distance_total, steps))

    return results


def run_baseline(episodes=150):
    env = ParkingEnv()
    results = []

    for _ in range(episodes):
        state = env.reset()
        done = False
        total_reward = 0
        distance_total = 0
        steps = 0
        final_info = {}

        while not done:
            steps += 1
            valid_actions = env.available_actions()
            action = choose_nearest_slot(valid_actions)
            state, reward, done, final_info = env.step(action)
            total_reward += reward
            distance_total += normalized_distance(action, env.slot_count)

        results.append(_episode_result(total_reward, final_info, distance_total, steps))

    return results


def choose_best_valid_action(action_values, valid_actions):
    if not valid_actions:
        return None
    if not action_values:
        return choose_nearest_slot(valid_actions)
    return max(valid_actions, key=lambda action: action_values.get(action, 0))


def choose_policy_action(policy, state, env, valid_actions):
    if isinstance(policy, dict) and policy.get("type") == "dqn_numpy":
        model = DQNModel.from_policy(policy)
        state_vector = encode_dqn_state(state, env)
        q_values = model.predict(state_vector)
        return max(valid_actions, key=lambda action: q_values[action]) if valid_actions else None
    action_values = policy.get(state, {})
    return choose_best_valid_action(action_values, valid_actions)


def policy_environment_kwargs(policy):
    if not isinstance(policy, dict) or policy.get("type") != "dqn_numpy":
        return {}
    metadata = policy.get("metadata", {})
    environment = metadata.get("config", {}).get("environment", {})
    return environment if isinstance(environment, dict) else {}


def choose_nearest_slot(valid_actions):
    return min(valid_actions) if valid_actions else None


def encode_dqn_state(state, env):
    occupancy = list(state[: env.slot_count])
    waiting_bucket = state[-2] / 3
    traffic_bucket = state[-1] / 3
    zone_size = max(1, env.slot_count // 3)
    zone_congestion = []
    for start in range(0, env.slot_count, zone_size):
        if len(zone_congestion) == 3:
            break
        zone = occupancy[start : start + zone_size]
        zone_congestion.append(sum(zone) / max(1, len(zone)))
    while len(zone_congestion) < 3:
        zone_congestion.append(0)
    availability = [1 - value for value in occupancy]
    return occupancy + zone_congestion + [waiting_bucket, traffic_bucket] + availability


def normalized_distance(action, slot_count):
    if action is None:
        return 1.0
    return action / max(1, slot_count - 1)


def _episode_result(total_reward, info, distance_total, steps):
    return {
        "reward": round(total_reward, 3),
        "cars_served": info.get("cars_served", 0),
        "rejected_cars": info.get("rejected_cars", 0),
        "occupancy_rate": info.get("occupancy_rate", 0),
        "average_wait": info.get("average_wait", 0),
        "average_congestion": info.get("traffic_level", 0),
        "average_distance": round(distance_total / max(1, steps), 3),
        "throughput": info.get("cars_served", 0),
        "waiting_queue_length": info.get("waiting_cars", 0),
    }


def summarize(results):
    return {
        "average_reward": round(statistics.mean(row["reward"] for row in results), 3),
        "average_cars_served": round(statistics.mean(row["cars_served"] for row in results), 3),
        "average_rejected_cars": round(
            statistics.mean(row["rejected_cars"] for row in results),
            3,
        ),
        "average_occupancy": round(
            statistics.mean(row["occupancy_rate"] for row in results),
            3,
        ),
        "average_wait": round(statistics.mean(row["average_wait"] for row in results), 3),
        "average_congestion": round(
            statistics.mean(row["average_congestion"] for row in results),
            3,
        ),
        "average_path_distance": round(
            statistics.mean(row["average_distance"] for row in results),
            3,
        ),
        "throughput": round(statistics.mean(row["throughput"] for row in results), 3),
        "waiting_queue_length": round(
            statistics.mean(row["waiting_queue_length"] for row in results),
            3,
        ),
    }


def main():
    policy_path = MODELS_DIR / "policy_v1.pkl"
    if not policy_path.exists():
        raise FileNotFoundError("Train the RL agent first: python rl/train.py")

    policy = load_q_table(policy_path)
    rl_rewards = run_policy(policy)
    baseline_rewards = run_baseline()
    rl_summary = summarize(rl_rewards)
    baseline_summary = summarize(baseline_rewards)
    summary = {
        "rl": rl_summary,
        "baseline_nearest_slot": baseline_summary,
        "reward_lift": round(
            rl_summary["average_reward"] - baseline_summary["average_reward"],
            3,
        ),
        "episodes": len(rl_rewards),
    }

    EXPERIMENTS_DIR.mkdir(exist_ok=True)
    with (EXPERIMENTS_DIR / "evaluation_summary.json").open("w") as file:
        json.dump(summary, file, indent=2)

    with (EXPERIMENTS_DIR / "evaluation_summary.txt").open("w") as file:
        file.write("RL Smart Parking Evaluation Summary\n")
        file.write("===================================\n")
        file.write(f"Episodes: {summary['episodes']}\n")
        file.write(f"RL average reward: {rl_summary['average_reward']}\n")
        file.write(
            f"Baseline average reward: {baseline_summary['average_reward']}\n"
        )
        file.write(f"Reward lift: {summary['reward_lift']}\n")
        file.write(f"RL average occupancy: {rl_summary['average_occupancy']}\n")
        file.write(
            f"Baseline average occupancy: {baseline_summary['average_occupancy']}\n"
        )

    with (EXPERIMENTS_DIR / "comparison_rewards.csv").open("w", newline="") as file:
        fieldnames = [
            "episode",
            "rl_reward",
            "baseline_reward",
            "rl_occupancy",
            "baseline_occupancy",
            "rl_wait",
            "baseline_wait",
            "rl_throughput",
            "baseline_throughput",
            "rl_waiting_queue_length",
            "baseline_waiting_queue_length",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for index, (rl_reward, baseline_reward) in enumerate(
            zip(rl_rewards, baseline_rewards),
            start=1,
        ):
            writer.writerow(
                {
                    "episode": index,
                    "rl_reward": rl_reward["reward"],
                    "baseline_reward": baseline_reward["reward"],
                    "rl_occupancy": rl_reward["occupancy_rate"],
                    "baseline_occupancy": baseline_reward["occupancy_rate"],
                    "rl_wait": rl_reward["average_wait"],
                    "baseline_wait": baseline_reward["average_wait"],
                    "rl_throughput": rl_reward["throughput"],
                    "baseline_throughput": baseline_reward["throughput"],
                    "rl_waiting_queue_length": rl_reward["waiting_queue_length"],
                    "baseline_waiting_queue_length": baseline_reward["waiting_queue_length"],
                }
            )

    print(summary)


if __name__ == "__main__":
    main()
