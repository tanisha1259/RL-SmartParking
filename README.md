# RL-SmartParking

RL-SmartParking is a reinforcement learning based smart parking allocation system. The project combines a Q-learning training pipeline, a simulated parking environment, a Flask backend API, and a React frontend dashboard to study how data-driven parking allocation can reduce waiting time, improve slot utilization, and support more efficient urban mobility.

The system is structured as a compact MLOps project: model behavior is configured through YAML files, training runs produce reproducible artifacts, experiment metrics are appended to a persistent results ledger, policies are saved for inference, and backend validation is automated through GitHub Actions.

## Project Overview

Urban parking facilities often suffer from inefficient slot assignment, long queues, uneven zone utilization, and congestion near high-demand areas. This project models parking allocation as a sequential decision-making problem in which an agent observes the parking state and chooses a slot allocation action.

The application includes:

- A parking-lot simulator that models arrivals, departures, waiting queues, occupancy, and congestion.
- A Q-learning agent that learns slot allocation policies through interaction with the simulator.
- A Flask backend that exposes parking state, metrics, queueing, allocation, and removal APIs.
- A React + Vite frontend for interactive parking visualization.
- MLOps additions for configuration management, experiment tracking, logging, Docker execution, and CI validation.

## SDG Mapping

This project aligns most directly with **United Nations Sustainable Development Goal 11: Sustainable Cities and Communities**.

Parking inefficiency contributes to congestion, longer search times, higher fuel usage, increased emissions, and poor use of urban infrastructure. By improving parking allocation decisions, the system supports SDG 11 through:

- Reduced vehicle waiting time inside and around parking facilities.
- More balanced occupancy across parking zones.
- Lower congestion pressure from queues and inefficient slot searching.
- Data-driven monitoring of operational metrics such as wait time, queue length, and policy performance.
- A reproducible experimentation framework for evaluating intelligent transport interventions.

## RL Methodology

The parking allocation task is treated as a reinforcement learning problem:

- **Environment:** The simulated parking lot in `sim/parking_env.py`.
- **Agent:** The Q-learning agent in `rl/q_learning.py`.
- **State:** A discrete representation of occupied slots, waiting pressure, and traffic pressure.
- **Action:** Selection of a parking slot from the available slots.
- **Reward:** A composite signal that rewards successful allocation, efficient occupancy, queue reduction, and zone balance while penalizing invalid decisions, waiting, congestion, and inefficient allocation.
- **Episode:** A fixed-length simulator run consisting of multiple parking arrival/departure steps.

This design keeps the state and action spaces interpretable while still demonstrating the core reinforcement learning cycle: observe state, choose action, receive reward, update policy, and repeat.

## Q-Learning Explanation

Q-learning is a model-free reinforcement learning algorithm that learns the expected utility of taking an action in a given state. The learned values are stored in a Q-table:

```text
Q(state, action) -> expected future reward
```

During training, the agent uses an epsilon-greedy strategy:

- With probability `epsilon`, it explores by selecting a random valid action.
- Otherwise, it exploits the current Q-table by choosing the highest-value valid action.

After each action, the Q-value is updated using:

```text
Q(s, a) = Q(s, a) + alpha * [reward + gamma * max(Q(s_next, a_next)) - Q(s, a)]
```

Where:

- `alpha` is the learning rate.
- `gamma` is the discount factor for future rewards.
- `epsilon` controls exploration.
- `epsilon_decay` gradually shifts behavior from exploration to exploitation.

All Q-learning hyperparameters are managed through YAML configuration files in `configs/`.

## Folder Structure

```text
backend/              Flask API and backend inference helper
backend/routes/       API route definitions
backend/rl/           Runtime policy loading and allocation logic
configs/              YAML configuration files for training and CI
docker/               Legacy backend Dockerfile
experiments/          Experiment summaries, rewards, and result tracking
frontend/             React + Vite frontend dashboard
logs/                 Training log output
models/               Saved Q-learning policy artifacts
plots/                Generated evaluation plots
rl/                   Q-learning agent, training, config, logging, tracking
sim/                  Parking environment simulator
.github/workflows/    GitHub Actions CI workflows
```

## Installation

Use Python 3.11 for the backend and training pipeline.

```bash
python -m venv .venv
```

On Windows:

```bash
.venv\Scripts\activate
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

Install Python dependencies:

```bash
pip install -r backend/requirements.txt
```

For the frontend:

```bash
cd frontend
npm install
```

## Reproducibility Steps

Training is configuration-driven. To reproduce a run, select a YAML config from `configs/` and pass it to the training script.

Baseline experiment:

```bash
python rl/train.py --config configs/qlearning_v1.yaml
```

Exploration-focused experiment:

```bash
python rl/train.py --config configs/qlearning_v2.yaml
```

Default canonical config:

```bash
python rl/train.py --config configs/qlearning.yaml
```

CI uses a lightweight configuration:

```bash
python rl/train.py --config configs/qlearning_ci.yaml
```

Each run creates a unique `run_id`, saves run-specific outputs, appends metrics to `experiments/results.csv`, and writes readable INFO logs to `logs/training.log`.

## Running Backend And Frontend

Run the backend API:

```bash
python -m flask --app backend.app:create_app run --host=0.0.0.0 --port=5001
```

The backend is available at:

```text
http://localhost:5001
```

Useful backend endpoints include:

- `GET /`
- `GET /slots`
- `GET /metrics`
- `POST /enqueue`
- `POST /allocate`
- `POST /remove`

Run the frontend:

```bash
cd frontend
npm run dev
```

The frontend dashboard is available at:

```text
http://localhost:5174
```

## Docker Usage

The backend can be containerized and run through Docker Compose from the project root:

```bash
docker compose up
```

To rebuild the image after dependency or Dockerfile changes:

```bash
docker compose up --build
```

Docker Compose builds the backend image from the root `Dockerfile`, installs dependencies from `backend/requirements.txt`, and exposes the Flask API on port `5001`.

```text
http://localhost:5001
```

The Docker configuration does not hardcode local machine paths.

## Experiment Tracking

Experiment tracking is implemented with lightweight CSV-based logging.

After every training run, one row is appended to:

```text
experiments/results.csv
```

Tracked fields include:

- `run_id`
- `timestamp`
- `episodes`
- `epsilon`
- `learning_rate`
- `gamma`
- `average_reward`
- `average_wait_time`

The training script also writes run-specific files:

- `experiments/rewards_<run_id>.csv`
- `experiments/occupancy_<run_id>.csv`
- `experiments/training_summary_<run_id>.json`
- `experiments/master_rewards.csv`

Logs are written to:

```text
logs/training.log
```

The logs include episode number, reward, chosen parking slot, epsilon value, and allocation success or failure.

## Policy Saving

After training, the learned Q-table policy is serialized with `pickle` and saved in the `models/` directory. The model filename is controlled by the selected YAML config:

```yaml
training:
  model_name: "policy_v1.pkl"
```

Saved policies are used by the backend inference helper to allocate parking slots. If no saved policy is available, the backend falls back to a simple nearest/free-slot style behavior so API execution remains stable.

## CI/CD

GitHub Actions is configured in:

```text
.github/workflows/test.yml
```

The workflow runs on every push and performs the following checks:

- Checks out the repository.
- Sets up Python 3.11.
- Installs backend Python dependencies.
- Compiles backend, RL, and simulator modules.
- Smoke tests the Flask API.
- Runs a lightweight training job using `configs/qlearning_ci.yaml`.

Any dependency, import, backend, or training execution error fails the workflow.

## Monitoring Plan

In a real-world deployment, the following metrics should be monitored continuously:

- **Average wait time:** Measures whether the policy is reducing queue delay.
- **Queue length:** Detects congestion buildup before it affects surrounding roads.
- **Occupancy percentage:** Tracks whether parking capacity is being used efficiently.
- **Zone balance:** Identifies whether the policy overuses particular regions of the lot.
- **Allocation success rate:** Measures the proportion of requests that receive valid slots.
- **Rejected cars:** Indicates capacity pressure or poor allocation behavior.
- **Average reward:** Provides a proxy for policy quality over time.
- **Policy drift:** Detects degradation when real traffic patterns diverge from training assumptions.

Operationally, these metrics could be exported to a dashboard such as Grafana or a managed observability platform. Alerts should be configured for sustained reward degradation, rising wait time, excessive rejection rates, and sudden changes in occupancy behavior.

## Future Improvements

- Add automated unit tests for the simulator, Q-learning updates, and backend routes.
- Add model versioning with metadata for config hash, Git commit, and training timestamp.
- Introduce MLflow or another experiment tracking platform for richer run comparison.
- Add policy evaluation gates before promoting a newly trained policy.
- Extend the simulator with time-of-day demand patterns and zone-specific traffic behavior.
- Add support for containerized frontend execution in Docker Compose.
- Add API authentication and production-ready server execution with Gunicorn.
- Add live monitoring dashboards for wait time, occupancy, and allocation success.
- Explore deep reinforcement learning when the state space grows beyond tabular Q-learning.

## Evaluation

Run evaluation and plotting scripts after training:

```bash
python compare.py
python plot_rewards.py
```

These scripts compare the learned policy against a baseline strategy and generate experiment artifacts for analysis.
