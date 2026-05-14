class StateEncoder:
    """Converts rich simulator state into a stable vector for future DQN input."""

    def encode(self, observation):
        occupancy = [
            observation["occupancy_map"][slot_id]
            for slot_id in sorted(observation["occupancy_map"])
        ]
        congestion = []
        for zone_id in ("A", "B", "C"):
            zone = observation["zone_congestion"].get(zone_id, {})
            congestion.extend(
                [
                    round(zone.get("occupancy_percentage", 0) / 100, 3),
                    round(zone.get("congestion_score", 0), 3),
                    round(zone.get("traffic_density", 0), 3),
                ]
            )
        position = observation["incoming_vehicle_position"]
        return occupancy + congestion + [position["x"] / 900, position["y"] / 560]
