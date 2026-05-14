class CongestionEngine:
    """Tracks zone occupancy and in-flight vehicles for allocation and heatmaps."""

    def __init__(self, zones):
        self.zones = [zone["id"] for zone in zones]

    def calculate(self, slots, moving_vehicles):
        stats = {}
        for zone_id in self.zones:
            zone_slots = [slot for slot in slots if slot["zone"] == zone_id]
            occupied = sum(1 for slot in zone_slots if self._is_active(slot))
            reserved = sum(1 for slot in zone_slots if slot.get("status") == "reserved")
            parked = sum(1 for slot in zone_slots if slot.get("status") == "occupied")
            moving = sum(
                1
                for vehicle in moving_vehicles
                if vehicle.get("zone") == zone_id and vehicle.get("status") == "moving"
            )
            total = len(zone_slots)
            occupancy_percentage = (occupied / total) * 100 if total else 0
            traffic_density = moving / max(total, 1)
            moving_vehicle_pressure = moving / max(total, 1)
            reservation_pressure = reserved / max(total, 1)
            congestion_score = (
                (occupied / max(total, 1)) * 0.55
                + moving_vehicle_pressure * 0.30
                + reservation_pressure * 0.15
            )
            stats[zone_id] = {
                "zone": zone_id,
                "total_slots": total,
                "occupied_slots": occupied,
                "reserved_slots": reserved,
                "parked_slots": parked,
                "moving_vehicles": moving,
                "available_slots": total - occupied,
                "occupancy_percentage": round(occupancy_percentage, 2),
                "traffic_density": round(traffic_density, 3),
                "congestion_score": round(congestion_score, 3),
            }
        return stats

    def _is_active(self, slot):
        return slot.get("occupied", False) or slot.get("status", "available") != "available"
