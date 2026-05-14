from copy import deepcopy
from pathlib import Path
import json


LAYOUT_PATH = Path(__file__).resolve().parents[1] / "data" / "parkingLayout.json"


class ParkingEnvironment:
    """Owns spatial parking state while exposing DQN-friendly observations."""

    def __init__(self, layout_path=LAYOUT_PATH):
        self.layout_path = Path(layout_path)
        self.layout = self._load_layout()
        self.slots = deepcopy(self.layout["slots"])

    def _load_layout(self):
        with self.layout_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def reset(self):
        self.slots = deepcopy(self.layout["slots"])
        return self.observe({}, self.layout["entry"])

    def get_layout(self):
        layout = deepcopy(self.layout)
        layout["slots"] = self.get_slots()
        return layout

    def get_slots(self):
        return deepcopy(self.slots)

    def free_slots(self):
        return [slot for slot in self.slots if not slot["occupied"]]

    def occupy(self, slot_id, car_id):
        slot = self.find_slot(slot_id)
        if slot is None or slot["occupied"]:
            return None
        slot["occupied"] = True
        slot["car_id"] = car_id
        return deepcopy(slot)

    def release(self, slot_id):
        slot = self.find_slot(slot_id)
        if slot is None:
            return None
        slot["occupied"] = False
        slot["car_id"] = None
        return deepcopy(slot)

    def find_slot(self, slot_id):
        normalized_id = str(slot_id).upper() if slot_id is not None else None
        for slot in self.slots:
            if slot["id"] == normalized_id:
                return slot
        return None

    def observe(self, zone_congestion, incoming_position):
        return {
            "occupancy_map": {
                slot["id"]: 1 if slot["occupied"] else 0 for slot in self.slots
            },
            "zone_congestion": zone_congestion,
            "incoming_vehicle_position": incoming_position,
            "available_actions": [slot["id"] for slot in self.free_slots()],
        }
