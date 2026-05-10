import random
from collections import deque


class ParkingEnv:
    """Small parking-lot simulator used by the Q-learning agent.

    State is intentionally simple and discrete so beginners can inspect the
    Q-table: occupied slots, waiting pressure, and traffic pressure.
    """

    def __init__(
        self,
        slot_count=12,
        max_steps=80,
        arrival_chance=0.75,
        departure_chance=0.12,
        max_waiting=8,
        target_occupancy=0.85,
        seed=None,
    ):
        self.slot_count = slot_count
        self.max_steps = max_steps
        self.arrival_chance = arrival_chance
        self.departure_chance = departure_chance
        self.max_waiting = max_waiting
        self.target_occupancy = target_occupancy
        self.random = random.Random(seed)
        self.reset()

    def reset(self):
        self.slots = [None for _ in range(self.slot_count)]
        self.waiting_cars = deque()
        self.steps = 0
        self.next_car_id = 1
        self.cars_served = 0
        self.cars_arrived = 0
        self.rejected_cars = 0
        self.total_wait_time = 0
        self.traffic_level = 0
        self._simulate_arrivals()
        return self._state()

    def _state(self):
        occupied = tuple(1 if car else 0 for car in self.slots)
        waiting_bucket = min(len(self.waiting_cars), 3)
        traffic_bucket = min(self.traffic_level, 3)
        return occupied + (waiting_bucket, traffic_bucket)

    def available_actions(self):
        if not self.waiting_cars:
            return []
        return [index for index, car in enumerate(self.slots) if car is None]

    def step(self, action):
        self.steps += 1
        reward = 0.0

        self._simulate_departures()
        self._simulate_arrivals()
        reward += self._apply_waiting_penalty()

        if action is None:
            reward -= 2.0 if self.waiting_cars else 0.2
        elif action not in range(self.slot_count):
            reward -= 8.0
        elif self.slots[action] is not None:
            reward -= 8.0
        elif not self.waiting_cars:
            reward -= 1.0
        else:
            reward += self._park_next_car(action)

        reward += self._occupancy_reward()
        reward -= self._congestion_penalty()

        done = self.steps >= self.max_steps
        info = self._info()
        return self._state(), round(reward, 3), done, info

    def _simulate_arrivals(self):
        self.traffic_level = self._sample_traffic_level()
        arrival_attempts = 1 if self.random.random() < self.arrival_chance else 0
        if self.traffic_level >= 2 and self.random.random() < 0.45:
            arrival_attempts += 1

        for _ in range(arrival_attempts):
            if len(self.waiting_cars) >= self.max_waiting:
                self.rejected_cars += 1
                continue

            self.waiting_cars.append(
                {
                    "id": f"CAR-{self.next_car_id:04d}",
                    "wait": 0,
                    "patience": self.random.randint(4, 10),
                }
            )
            self.next_car_id += 1
            self.cars_arrived += 1

    def _sample_traffic_level(self):
        roll = self.random.random()
        if roll < 0.45:
            return 1
        if roll < 0.8:
            return 2
        return 3

    def _simulate_departures(self):
        for index, car in enumerate(self.slots):
            if car and self.random.random() < self.departure_chance:
                self.slots[index] = None

    def _apply_waiting_penalty(self):
        penalty = 0.0
        still_waiting = deque()

        while self.waiting_cars:
            car = self.waiting_cars.popleft()
            car["wait"] += 1
            self.total_wait_time += 1
            penalty -= 0.35

            if car["wait"] > car["patience"]:
                self.rejected_cars += 1
                penalty -= 4.0
            else:
                still_waiting.append(car)

        self.waiting_cars = still_waiting
        return penalty

    def _park_next_car(self, action):
        car = self.waiting_cars.popleft()
        self.slots[action] = car
        self.cars_served += 1

        distance_penalty = action / max(1, self.slot_count - 1)
        queue_relief_bonus = min(3.0, 0.5 * len(self.waiting_cars))
        traffic_bonus = 1.5 if self.traffic_level >= 2 and action < self.slot_count / 2 else 0
        balanced_zone_bonus = self._zone_balance_bonus(action)
        waiting_penalty = 0.25 * car["wait"]

        return 12.0 + queue_relief_bonus + traffic_bonus + balanced_zone_bonus - distance_penalty - waiting_penalty

    def _zone_balance_bonus(self, action):
        zone_size = max(1, self.slot_count // 3)
        zone_start = (action // zone_size) * zone_size
        zone_end = min(self.slot_count, zone_start + zone_size)
        zone_occupied = sum(1 for car in self.slots[zone_start:zone_end] if car)
        zone_ratio = zone_occupied / max(1, zone_end - zone_start)
        return 1.0 if zone_ratio <= self.target_occupancy else -1.0

    def _occupancy_reward(self):
        occupancy = self.occupancy_rate
        if occupancy <= self.target_occupancy:
            return 2.0 * occupancy
        return -3.0 * (occupancy - self.target_occupancy)

    def _congestion_penalty(self):
        queue_pressure = len(self.waiting_cars) / max(1, self.max_waiting)
        traffic_pressure = self.traffic_level / 3
        return 2.5 * queue_pressure * traffic_pressure

    @property
    def occupancy_rate(self):
        return sum(1 for car in self.slots if car) / self.slot_count

    def _info(self):
        average_wait = self.total_wait_time / self.cars_arrived if self.cars_arrived else 0
        return {
            "cars_arrived": self.cars_arrived,
            "cars_served": self.cars_served,
            "rejected_cars": self.rejected_cars,
            "waiting_cars": len(self.waiting_cars),
            "traffic_level": self.traffic_level,
            "occupancy_rate": round(self.occupancy_rate, 3),
            "average_wait": round(average_wait, 3),
        }
