
import pickle
import random
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = ROOT_DIR / "models" / "q_policy.pkl"


def load_policy(policy_path=DEFAULT_POLICY_PATH):
    """Load the trained Q-table from disk.

    New policies are stored with metadata. The fallback keeps older plain
    Q-table pickle files usable.
    """
    policy_path = Path(policy_path)
    if not policy_path.exists():
        return {}

    with policy_path.open("rb") as file:
        policy = pickle.load(file)

    if isinstance(policy, dict) and "q_table" in policy:
        return policy["q_table"]
    return policy


def allocate_best_slot(state, policy=None, free_slots=None):
    """Return the best free slot id for a parking state.

    Args:
        state: tuple produced by the simulator or ParkingAllocator.
        policy: optional Q-table. If omitted, the saved policy is loaded.
        free_slots: optional list of slot ids that are currently free.
    """
    policy = policy if policy is not None else load_policy()
    occupied_flags = state[:-2] if len(state) > 2 else state
    free_slots = free_slots or [
        index for index, occupied in enumerate(occupied_flags) if occupied == 0
    ]

    if not free_slots:
        return None

    action_values = policy.get(tuple(state), {})
    if not action_values:
        return min(free_slots)

    return max(free_slots, key=lambda action: action_values.get(action, 0.0))

class ParkingAllocator:
    def __init__(self, slot_count=12):
        self.slot_count = slot_count
        self.slots = [
            {"id": index, "occupied": False, "car_id": None}
            for index in range(1, slot_count + 1)
        ]

        self.total_requests = 0
        self.successful_allocations = 0
        self.policy = load_policy()

        self.next_car_number = 1
        self.cars_processed = 0


    def get_slots(self):
        return self.slots

    def get_metrics(self):
        occupied = sum(1 for slot in self.slots if slot["occupied"])
        free = self.slot_count - occupied
        occupancy_percentage = (occupied / self.slot_count) * 100
        return {
            "total_slots": self.slot_count,
            "occupied_slots": occupied,
            "free_slots": free,
            "cars_processed": self.cars_processed,
            "occupancy_percentage": round(occupancy_percentage, 2),
        }

    def allocate(self):
        slot = self._nearest_free_slot()

        if slot is None:
            return {
                "allocated": False,
                "message": "No free parking slots available.",
                "slot": None,
                "metrics": self.get_metrics(),
            }

        slot["occupied"] = True
        slot["car_id"] = self._next_car_id()
        self.cars_processed += 1

        return {
            "allocated": True,
            "message": "Car allocated successfully.",
            "slot": slot,
            "metrics": self.get_metrics(),
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

        state = self._state()
        free_ids = [slot["id"] for slot in free_slots]
        best_slot_id = allocate_best_slot(state, policy=self.policy, free_slots=free_ids)

        if best_slot_id is None:
            return random.choice(free_slots)
        return self.slots[best_slot_id]

    def _state(self):
        occupied = tuple(1 if slot["occupied"] else 0 for slot in self.slots)
        waiting_bucket = 1
        traffic_bucket = self._traffic_bucket()
        return occupied + (waiting_bucket, traffic_bucket)

    def _traffic_bucket(self):
        occupied_ratio = sum(1 for slot in self.slots if slot["occupied"]) / self.slot_count
        if occupied_ratio < 0.5:
            return 1
        if occupied_ratio < 0.8:
            return 2
        return 3

        state = tuple(1 if slot["occupied"] else 0 for slot in self.slots)
        action_values = self.policy.get(state)

    def remove(self, slot_id):
        slot = self._find_slot(slot_id)

        if slot is None:
            return {
                "removed": False,
                "message": "A valid slot_id is required.",
                "slot": None,
                "metrics": self.get_metrics(),
            }

        if not slot["occupied"]:
            return {
                "removed": False,
                "message": f"Slot {slot['id']} is already free.",
                "slot": slot,
                "metrics": self.get_metrics(),
            }

        removed_car_id = slot["car_id"]
        slot["occupied"] = False
        slot["car_id"] = None

        return {
            "removed": True,
            "message": f"Car {removed_car_id} removed from slot {slot['id']}.",
            "slot": slot,
            "metrics": self.get_metrics(),
        }

    def _nearest_free_slot(self):
        for slot in self.slots:
            if not slot["occupied"]:
                return slot

        return None

    def _next_car_id(self):
        car_id = f"CAR-{self.next_car_number:03d}"
        self.next_car_number += 1
        return car_id

    def _find_slot(self, slot_id):
        try:
            requested_id = int(slot_id)
        except (TypeError, ValueError):
            return None

        for slot in self.slots:
            if slot["id"] == requested_id:
                return slot

        return None

