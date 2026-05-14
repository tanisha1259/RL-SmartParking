from .rewardEngine import RewardEngine


class SmartSlotAllocator:
    """Weighted allocator that can later be swapped for a trained DQN policy."""

    def __init__(self, pathfinder, distance_weight=0.5, congestion_weight=0.3, density_weight=0.2):
        self.pathfinder = pathfinder
        self.reward_engine = RewardEngine()
        self.weights = {
            "distance": distance_weight,
            "congestion": congestion_weight,
            "density": density_weight,
        }

    def choose_slot(self, free_slots, zone_stats):
        if not free_slots:
            return None

        candidates = []
        for slot in free_slots:
            path = self.pathfinder.path_to_slot(slot)
            path_length = self.pathfinder.path_length(path)
            zone = zone_stats.get(slot["zone"], {})
            congestion = zone.get("congestion_score", 0)
            density = zone.get("occupancy_percentage", 0) / 100
            score = (
                self.weights["distance"] * (path_length / 1000)
                + self.weights["congestion"] * congestion
                + self.weights["density"] * density
            )
            candidates.append(
                {
                    "slot": slot,
                    "path": path,
                    "path_length": round(path_length, 2),
                    "score": round(score, 4),
                    "reward": self.reward_engine.allocation_reward(slot, path_length, zone_stats),
                }
            )

        return min(candidates, key=lambda candidate: candidate["score"])
