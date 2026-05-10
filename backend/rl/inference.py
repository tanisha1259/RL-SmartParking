class ParkingAllocator:
    def __init__(self, slot_count=12):
        self.slot_count = slot_count
        self.slots = [
            {"id": index, "occupied": False, "car_id": None}
            for index in range(1, slot_count + 1)
        ]
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
