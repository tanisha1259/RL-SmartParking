import random


class ParkingEnv:
    def __init__(self, slot_count=12, max_steps=40, departure_chance=0.15):
        self.slot_count = slot_count
        self.max_steps = max_steps
        self.departure_chance = departure_chance
        self.reset()

    def reset(self):
        self.slots = [0 for _ in range(self.slot_count)]
        self.steps = 0
        self.cars_served = 0
        return self._state()

    def _state(self):
        return tuple(self.slots)

    def available_actions(self):
        return [index for index, occupied in enumerate(self.slots) if occupied == 0]

    def step(self, action):
        self.steps += 1
        reward = 0
        done = False

        if action is None:
            reward = -10
        elif self.slots[action] == 0:
            self.slots[action] = 1
            self.cars_served += 1
            reward = self._allocation_reward(action)
        else:
            reward = -5

        self._simulate_departures()

        if self.steps >= self.max_steps:
            done = True

        if not self.available_actions():
            done = True

        info = {"cars_served": self.cars_served}
        return self._state(), reward, done, info

    def _allocation_reward(self, action):
        distance_penalty = action / max(1, self.slot_count - 1)
        utilization_bonus = sum(self.slots) / self.slot_count
        return 10 - distance_penalty + utilization_bonus

    def _simulate_departures(self):
        for index, occupied in enumerate(self.slots):
            if occupied and random.random() < self.departure_chance:
                self.slots[index] = 0
