import csv
import pickle
import sys
from pathlib import Path

from q_learning import QLearningAgent


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from sim.parking_env import ParkingEnv

MODELS_DIR = ROOT_DIR / "models"
EXPERIMENTS_DIR = ROOT_DIR / "experiments"


def train(episodes=500):
    env = ParkingEnv(slot_count=12, max_steps=40)
    agent = QLearningAgent(actions=range(env.slot_count))
    rewards = []

    for episode in range(1, episodes + 1):
        state = env.reset()
        total_reward = 0
        done = False

        while not done:
            valid_actions = env.available_actions()
            action = agent.choose_action(state, valid_actions)
            next_state, reward, done, _ = env.step(action)
            agent.learn(state, action, reward, next_state, done)
            state = next_state
            total_reward += reward

        agent.decay_epsilon()
        rewards.append(
            {
                "episode": episode,
                "reward": total_reward,
                "epsilon": round(agent.epsilon, 4),
            }
        )

    save_outputs(agent, rewards)
    print("Training complete.")
    print(f"Policy saved to {MODELS_DIR / 'q_policy.pkl'}")
    print(f"Rewards saved to {EXPERIMENTS_DIR / 'training_rewards.csv'}")


def save_outputs(agent, rewards):
    MODELS_DIR.mkdir(exist_ok=True)
    EXPERIMENTS_DIR.mkdir(exist_ok=True)

    with (MODELS_DIR / "q_policy.pkl").open("wb") as file:
        pickle.dump(dict(agent.q_table), file)

    with (EXPERIMENTS_DIR / "training_rewards.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["episode", "reward", "epsilon"])
        writer.writeheader()
        writer.writerows(rewards)


if __name__ == "__main__":
    train()
