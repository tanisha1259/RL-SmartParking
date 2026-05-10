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
        if not valid_actions:
            return None

        if random.random() < self.epsilon:
            return random.choice(valid_actions)

        values = self.q_table[state]
        return max(valid_actions, key=lambda action: values[action])

    def learn(self, state, action, reward, next_state, done):
        if action is None:
            return

        current_value = self.q_table[state][action]
        next_best = 0 if done else max(self.q_table[next_state].values())
        target = reward + self.discount_factor * next_best
        self.q_table[state][action] += self.learning_rate * (target - current_value)

    def decay_epsilon(self):
        self.epsilon = max(self.epsilon_min, self.epsilon * self.epsilon_decay)
