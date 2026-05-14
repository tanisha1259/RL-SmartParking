import random
from collections import deque


class ReplayBuffer:
    """Fixed-size experience replay buffer for lightweight DQN training."""

    def __init__(self, capacity, seed=None):
        self.capacity = capacity
        self.buffer = deque(maxlen=capacity)
        self.random = random.Random(seed)

    def push(self, state, action, reward, next_state, done, valid_actions):
        self.buffer.append((state, action, reward, next_state, done, tuple(valid_actions)))

    def sample(self, batch_size):
        return self.random.sample(self.buffer, min(batch_size, len(self.buffer)))

    def __len__(self):
        return len(self.buffer)
