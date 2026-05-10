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
            for index in range(slot_count)
        ]
        self.total_requests = 0
        self.successful_allocations = 0
        self.policy = load_policy()

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
