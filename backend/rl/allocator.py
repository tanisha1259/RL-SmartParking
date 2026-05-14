from math import sqrt

from .rewardEngine import RewardEngine


class SmartSlotAllocator:
    """Weighted allocator that can later be swapped for a trained DQN policy."""

    def __init__(
        self,
        pathfinder,
        layout,
        distance_weight=0.30,
        congestion_weight=0.25,
        density_weight=0.20,
        neighbor_weight=0.20,
        aisle_weight=0.15,
    ):
        self.pathfinder = pathfinder
        self.layout = layout
        self.reward_engine = RewardEngine()

        self.weights = {
            "distance": distance_weight,
            "congestion": congestion_weight,
            "density": density_weight,
            "neighbor": neighbor_weight,
            "aisle": aisle_weight,
        }

    def choose_slot(self, free_slots, zone_stats):
        if not free_slots:
            return None

        all_slots = self.layout["slots"]

        candidates = []

        for slot in free_slots:
            path = self.pathfinder.path_to_slot(slot)
            path_length = self.pathfinder.path_length(path)

            zone = zone_stats.get(slot["zone"], {})

            congestion = zone.get("congestion_score", 0)
            density = zone.get("occupancy_percentage", 0) / 100

            neighbor_penalty = self._neighbor_density(slot, all_slots)
            aisle_penalty = self._aisle_pressure(slot, all_slots)
            score = (
                self.weights["distance"] * (path_length / 1000)
                + self.weights["congestion"] * congestion
                + self.weights["density"] * density
                + self.weights["neighbor"] * neighbor_penalty
                + self.weights["aisle"] * aisle_penalty
            )

            candidates.append(
                {
                    "slot": slot,
                    "path": path,
                    "path_length": round(path_length, 2),
                    "neighbor_penalty": round(neighbor_penalty, 3),
                    "aisle_penalty": round(aisle_penalty, 3),
                    "score": round(score, 4),
                    "reward": self.reward_engine.allocation_reward(
                        slot,
                        path_length,
                        zone_stats,
                    ),
                }
            )

        return min(candidates, key=lambda candidate: candidate["score"])

    def _neighbor_density(self, target_slot, all_slots):
        occupied_neighbors = 0

        for slot in all_slots:
            if slot["id"] == target_slot["id"]:
                continue

            is_occupied = slot.get("occupied") or slot.get("status", "available") != "available"
            if not is_occupied:
                continue

            distance = sqrt(
                (slot["x"] - target_slot["x"]) ** 2
                + (slot["y"] - target_slot["y"]) ** 2
            )

            if distance < 130:
                occupied_neighbors += 1

        return occupied_neighbors / 4
    
    def _aisle_pressure(self, target_slot, all_slots):
        occupied_same_aisle = 0
        for slot in all_slots:
            is_occupied = slot.get("occupied") or slot.get("status", "available") != "available"
            if not is_occupied:
                continue
            if slot["aisleNode"] == target_slot["aisleNode"]:
                occupied_same_aisle += 1

        return occupied_same_aisle / 6
