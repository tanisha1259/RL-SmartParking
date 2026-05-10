import random
from collections import defaultdict


class QLearningAgent:
    def __init__(
        self,
        actions,
        learning_rate=0.1,
        discount_factor=0.95,
        epsilon=1.0,
        epsilon_min=0.05,
        epsilon_decay=0.995,
    ):
        self.actions = list(actions)
        self.learning_rate = learning_rate
        self.discount_factor = discount_factor
        self.epsilon = epsilon
        self.epsilon_min = epsilon_min
        self.epsilon_decay = epsilon_decay
        self.q_table = defaultdict(lambda: {action: 0.0 for action in self.actions})

    def choose_action(self, state, valid_actions):
        """Choose a slot with epsilon-greedy exploration."""
        if not valid_actions:
            return None

        if random.random() < self.epsilon:
            return random.choice(valid_actions)

        values = self.q_table[state]
        best_value = max(values[action] for action in valid_actions)
        best_actions = [action for action in valid_actions if values[action] == best_value]
        return random.choice(best_actions)

    def learn(self, state, action, reward, next_state, done, next_valid_actions=None):
        if action is None:
            return

        current_value = self.q_table[state][action]
        if done:
            next_best = 0
        elif next_valid_actions:
            next_values = self.q_table[next_state]
            next_best = max(next_values[next_action] for next_action in next_valid_actions)
        else:
            next_best = 0

        target = reward + self.discount_factor * next_best
        self.q_table[state][action] += self.learning_rate * (target - current_value)

    def decay_epsilon(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)

    def export_policy(self):
        """Return a plain dict that can be safely written with pickle."""
        return {
            "actions": self.actions,
            "q_table": {state: dict(values) for state, values in self.q_table.items()},
            "epsilon": self.epsilon,
            "learning_rate": self.learning_rate,
            "discount_factor": self.discount_factor,
        }
