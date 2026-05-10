import pickle
import random
from pathlib import Path


class ParkingAllocator:
    def __init__(self, slot_count=12):
        self.slot_count = slot_count
        self.slots = [
            {"id": index, "occupied": False, "car_id": None}
            for index in range(slot_count)
        ]
        self.total_requests = 0
        self.successful_allocations = 0
        self.policy = self._load_policy()

    def _load_policy(self):
        policy_path = Path(__file__).resolve().parents[2] / "models" / "q_policy.pkl"
        if not policy_path.exists():
            return {}

        with policy_path.open("rb") as file:
            return pickle.load(file)

    def get_slots(self):
        return self.slots

    def get_metrics(self):
        occupied = sum(1 for slot in self.slots if slot["occupied"])
        free = self.slot_count - occupied
        success_rate = (
            self.successful_allocations / self.total_requests
            if self.total_requests
            else 0
        )
        return {
            "total_slots": self.slot_count,
            "occupied_slots": occupied,
            "free_slots": free,
            "total_requests": self.total_requests,
            "successful_allocations": self.successful_allocations,
            "success_rate": round(success_rate, 2),
        }

    def allocate(self, car_id=None):
        self.total_requests += 1
        free_slots = [slot for slot in self.slots if not slot["occupied"]]

        if not free_slots:
            return {
                "allocated": False,
                "message": "No free parking slots available.",
                "slot": None,
            }

        slot = self._select_slot(free_slots)
        slot["occupied"] = True
        slot["car_id"] = car_id or f"CAR-{self.total_requests:03d}"
        self.successful_allocations += 1

        return {
            "allocated": True,
            "message": "Car allocated successfully.",
            "slot": slot,
        }

    def remove(self, car_id=None, slot_id=None):
        occupied_slots = [slot for slot in self.slots if slot["occupied"]]

        if not occupied_slots:
            return {
                "removed": False,
                "message": "No occupied parking slots to free.",
                "slot": None,
            }

        slot = None
        if slot_id is not None:
            slot = next(
                (
                    occupied_slot
                    for occupied_slot in occupied_slots
                    if occupied_slot["id"] == slot_id
                ),
                None,
            )
        elif car_id:
            slot = next(
                (
                    occupied_slot
                    for occupied_slot in occupied_slots
                    if occupied_slot["car_id"] == car_id
                ),
                None,
            )
        else:
            slot = occupied_slots[-1]

        if slot is None:
            return {
                "removed": False,
                "message": "Could not find that parked car.",
                "slot": None,
            }

        freed_slot = slot.copy()
        slot["occupied"] = False
        slot["car_id"] = None

        return {
            "removed": True,
            "message": "Parking slot freed successfully.",
            "slot": freed_slot,
        }

    def _select_slot(self, free_slots):
        state = tuple(1 if slot["occupied"] else 0 for slot in self.slots)
        action_values = self.policy.get(state)

        if action_values:
            ranked_actions = sorted(
                action_values,
                key=action_values.get,
                reverse=True,
            )
            free_ids = {slot["id"] for slot in free_slots}
            for action in ranked_actions:
                if action in free_ids:
                    return self.slots[action]

        return random.choice(free_slots)
