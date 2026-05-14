from copy import deepcopy
from pathlib import Path
import json


LAYOUT_PATH = Path(__file__).resolve().parents[1] / "data" / "parkingLayout.json"


class ParkingEnvironment:
    """Owns spatial parking state while exposing DQN-friendly observations."""

    ACTIVE_STATUSES = {"reserved", "occupied"}

    def __init__(self, layout_path=LAYOUT_PATH):
        self.layout_path = Path(layout_path)
        self.layout = self._load_layout()
        self.slots = deepcopy(self.layout["slots"])
        self._sync_status()

    def _sync_status(self):
        for slot in self.slots:
            if "status" not in slot:
                slot["status"] = "occupied" if slot.get("occupied") else "available"
            if slot["status"] not in {"available", "reserved", "occupied"}:
                slot["status"] = "occupied" if slot.get("occupied") else "available"
            slot["occupied"] = slot["status"] in self.ACTIVE_STATUSES
            if slot["status"] == "available":
                slot["car_id"] = None

    def _load_layout(self):
        with self.layout_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def reset(self):
        self.slots = deepcopy(self.layout["slots"])
        self._sync_status()

        return self.observe(
            {},
            self.layout["entry"],
        )

    def get_layout(self):
        layout = deepcopy(self.layout)

        layout["slots"] = self.get_slots()

        return layout

    def get_slots(self):
        return deepcopy(self.slots)

    def free_slots(self):
        return [
            slot
            for slot in self.slots
            if self.is_available(slot)
        ]

    def reserve(self, slot_id, car_id):
        slot = self.find_slot(slot_id)

        if slot is None:
            return None

        if not self.is_available(slot):
            return None

        self._set_slot_state(slot, "reserved", car_id)

        return deepcopy(slot)

    def occupy(self, slot_id, car_id=None):
        slot = self.find_slot(slot_id)

        if slot is None:
            return None

        if slot["status"] == "available" and car_id is None:
            return None

        self._set_slot_state(slot, "occupied", car_id or slot.get("car_id"))

        return deepcopy(slot)

    def release(self, slot_id):
        slot = self.find_slot(slot_id)

        if slot is None:
            return None

        self._set_slot_state(slot, "available", None)

        return deepcopy(slot)

    def is_available(self, slot):
        return slot.get("status", "available") == "available" and not slot.get("occupied", False)

    def _set_slot_state(self, slot, status, car_id=None):
        slot["status"] = status
        slot["occupied"] = status in self.ACTIVE_STATUSES
        slot["car_id"] = car_id if status != "available" else None

    def find_slot(self, slot_id):
        normalized_id = (
            str(slot_id).upper()
            if slot_id is not None
            else None
        )

        for slot in self.slots:
            if slot["id"] == normalized_id:
                return slot

        return None

    def observe(self, zone_congestion, incoming_position):
        return {
            "occupancy_map": {
                slot["id"]: (
                    0
                    if self.is_available(slot)
                    else 1
                )
                for slot in self.slots
            },

            "zone_congestion": zone_congestion,

            "incoming_vehicle_position": incoming_position,

            "available_actions": [
                slot["id"]
                for slot in self.free_slots()
            ],
        }
