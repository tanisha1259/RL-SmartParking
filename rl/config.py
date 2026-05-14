from dataclasses import MISSING, dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class TrainingConfig:
    episodes: int
    model_name: str


@dataclass(frozen=True)
class EnvironmentConfig:
    slot_count: int
    max_steps: int
    arrival_chance: float
    departure_chance: float
    max_waiting: int
    target_occupancy: float
    seed: int | None = None

    def as_kwargs(self):
        return {
            "slot_count": self.slot_count,
            "max_steps": self.max_steps,
            "arrival_chance": self.arrival_chance,
            "departure_chance": self.departure_chance,
            "max_waiting": self.max_waiting,
            "target_occupancy": self.target_occupancy,
            "seed": self.seed,
        }


@dataclass(frozen=True)
class AgentConfig:
    learning_rate: float
    discount_factor: float
    epsilon_start: float
    epsilon_min: float
    epsilon_decay: float


@dataclass(frozen=True)
class QLearningConfig:
    training: TrainingConfig
    environment: EnvironmentConfig
    agent: AgentConfig
    raw: dict


def load_qlearning_config(config_path):
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as file:
        raw_config = yaml.safe_load(file) or {}

    _validate_required_sections(raw_config, path)
    training = _build_dataclass(TrainingConfig, raw_config["training"], "training", path)
    environment = _build_dataclass(
        EnvironmentConfig,
        raw_config["environment"],
        "environment",
        path,
    )
    agent = _build_dataclass(AgentConfig, raw_config["agent"], "agent", path)

    _validate_ranges(training, environment, agent, path)

    return QLearningConfig(
        training=training,
        environment=environment,
        agent=agent,
        raw=raw_config,
    )


def _validate_required_sections(config, path):
    required_sections = ("training", "environment", "agent")
    missing_sections = [section for section in required_sections if section not in config]
    if missing_sections:
        missing = ", ".join(missing_sections)
        raise ValueError(f"{path} is missing required section(s): {missing}")


def _build_dataclass(config_type, values, section, path):
    if not isinstance(values, dict):
        raise ValueError(f"{path} section '{section}' must be a mapping")

    required_fields = {
        field
        for field in config_type.__dataclass_fields__
        if config_type.__dataclass_fields__[field].default is MISSING
        and config_type.__dataclass_fields__[field].default_factory is MISSING
    }
    missing_fields = sorted(required_fields - values.keys())
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"{path} section '{section}' is missing field(s): {missing}")

    valid_fields = set(config_type.__dataclass_fields__)
    unknown_fields = sorted(values.keys() - valid_fields)
    if unknown_fields:
        unknown = ", ".join(unknown_fields)
        raise ValueError(f"{path} section '{section}' has unknown field(s): {unknown}")

    return config_type(**values)


def _validate_ranges(training, environment, agent, path):
    if training.episodes <= 0:
        raise ValueError(f"{path} training.episodes must be greater than zero")
    if environment.slot_count <= 0:
        raise ValueError(f"{path} environment.slot_count must be greater than zero")
    if environment.max_steps <= 0:
        raise ValueError(f"{path} environment.max_steps must be greater than zero")
    if environment.max_waiting <= 0:
        raise ValueError(f"{path} environment.max_waiting must be greater than zero")

    probability_fields = {
        "environment.arrival_chance": environment.arrival_chance,
        "environment.departure_chance": environment.departure_chance,
        "environment.target_occupancy": environment.target_occupancy,
        "agent.epsilon_start": agent.epsilon_start,
        "agent.epsilon_min": agent.epsilon_min,
        "agent.epsilon_decay": agent.epsilon_decay,
    }
    for name, value in probability_fields.items():
        if not 0 <= value <= 1:
            raise ValueError(f"{path} {name} must be between 0 and 1")

    if agent.learning_rate <= 0:
        raise ValueError(f"{path} agent.learning_rate must be greater than zero")
    if not 0 <= agent.discount_factor <= 1:
        raise ValueError(f"{path} agent.discount_factor must be between 0 and 1")
    if agent.epsilon_min > agent.epsilon_start:
        raise ValueError(f"{path} agent.epsilon_min cannot exceed agent.epsilon_start")
