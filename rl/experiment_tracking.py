import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


RESULT_FIELDS = [
    "run_id",
    "timestamp",
    "episodes",
    "epsilon",
    "learning_rate",
    "gamma",
    "average_reward",
    "congestion_score",
    "average_distance",
    "throughput",
    "average_wait_time",
]


@dataclass(frozen=True)
class ExperimentResult:
    run_id: str
    episodes: int
    epsilon: float
    learning_rate: float
    gamma: float
    average_reward: float
    average_wait_time: float
    congestion_score: float = 0.0
    average_distance: float = 0.0
    throughput: float = 0.0

    def to_row(self):
        return {
            "run_id": self.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "episodes": self.episodes,
            "epsilon": round(self.epsilon, 4),
            "learning_rate": self.learning_rate,
            "gamma": self.gamma,
            "average_reward": round(self.average_reward, 3),
            "congestion_score": round(self.congestion_score, 3),
            "average_distance": round(self.average_distance, 3),
            "throughput": round(self.throughput, 3),
            "average_wait_time": round(self.average_wait_time, 3),
        }


def append_experiment_result(results_path, result):
    path = Path(results_path)
    path.parent.mkdir(exist_ok=True)
    should_write_header = not path.exists() or path.stat().st_size == 0

    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=RESULT_FIELDS)
        if should_write_header:
            writer.writeheader()
        writer.writerow(result.to_row())
