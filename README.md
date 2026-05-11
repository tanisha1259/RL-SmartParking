# RL-SmartParking

Smart Parking Allocation System using Reinforcement Learning. 

**SDG 11 Alignment (Sustainable Cities and Communities):** By optimizing parking allocation, reducing search times, and balancing traffic across zones, this project actively reduces congestion, fuel waste, and air pollution in urban parking structures, heavily aligning with SDG 11.

This project is a full-stack MLOps pipeline with a Flask backend, React + Vite frontend, an MLOps-tracked Q-learning training loop, and a parking-lot simulator.

## Project Structure

```text
backend/      Flask API and RL inference helper
frontend/     React dashboard built with Vite
rl/           Q-learning agent and training script
sim/          Parking environment simulator
configs/      YAML configs for training reproducibility
models/       Saved policies (e.g. policy_v1.pkl)
experiments/  CSV and JSON experiment outputs tracking MLOps metrics
plots/        Generated charts
```

## Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m flask run --host=0.0.0.0 --port=5001
```
The API runs at `http://localhost:5001`.

## Frontend
```bash
cd frontend
npm install
npm run dev
```
The dashboard runs at `http://localhost:5174`.

## Train The RL Agent (MLOps Reproducibility)

To reproduce the experiments, you must supply a YAML configuration file. The training script uses this config, tracks hyperparameters, and generates a specific `run-id` for MLOps tracking.

**Experiment 1 (Baseline):**
```bash
python rl/train.py --config configs/qlearning_v1.yaml
```
**Experiment 2 (Exploration):**
```bash
python rl/train.py --config configs/qlearning_v2.yaml
```

Outputs will be saved with their respective run IDs:
- `models/policy_v1.pkl`
- `experiments/rewards_run_xxxx.csv`
- `experiments/training_summary_run_xxxx.json`

## Real-world Monitoring Plan (MLOps)
If this system were deployed in a real-world smart parking garage, we would monitor the following metrics using a dashboard (like Grafana):
1. **Average Wait Time in Queue:** To ensure the RL agent is efficiently prioritizing waiting cars over random allocation.
2. **Maximum Queue Length:** To ensure physical roads leading into the parking garage do not spill over into public city streets (SDG 11 tracking).
3. **Zone Occupancy Balance:** Tracking if the agent is correctly spreading cars out across the lot to prevent internal pedestrian/vehicular accidents and congestion.
4. **Policy Drift:** If the `average_reward` suddenly drops below historical baselines, it triggers an alert to retrain the Q-table (e.g., if traffic patterns change drastically).

## Evaluate
```bash
python compare.py
python plot_rewards.py
```
