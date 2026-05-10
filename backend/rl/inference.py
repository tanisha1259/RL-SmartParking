    def remove(self, car_id=None, slot_id=None):
        occupied_slots = [slot for slot in self.slots if slot["occupied"]]

        if not occupied_slots:
            return {
                "removed": False,
                "message": "No occupied parking slots to free.",
                "slot": None,
                "metrics": self.get_metrics(),
            }

        slot = None

        if slot_id is not None:
            slot = next(
                (
                    occupied_slot
                    for occupied_slot in occupied_slots
                    if occupied_slot["id"] == int(slot_id)
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