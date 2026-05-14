class RewardEngine:
    """Reward contract for future DQN training and current allocation scoring."""

    def score_reward(self, distance, congestion, occupancy_density):
        distance_penalty = distance / 1000
        congestion_penalty = congestion
        balance_reward = 1 - occupancy_density
        return round(balance_reward - distance_penalty - congestion_penalty, 4)

    def allocation_reward(self, slot, path_length, zone_stats):
        zone = zone_stats.get(slot["zone"], {})
        return self.score_reward(
            distance=path_length,
            congestion=zone.get("congestion_score", 0),
            occupancy_density=zone.get("occupancy_percentage", 0) / 100,
        )
