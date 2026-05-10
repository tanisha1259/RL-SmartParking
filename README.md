# RL-SmartParking

Smart Parking Allocation System using Reinforcement Learning.

This project is a beginner-friendly full-stack example with a Flask backend, React + Vite frontend, a small Q-learning training loop, and a parking-lot simulator.

## Project Structure

```text
backend/      Flask API and RL inference helper
frontend/     React dashboard built with Vite
rl/           Q-learning agent and training script
sim/          Parking environment simulator
models/       Saved policies
experiments/  CSV and JSON experiment outputs
plots/        Generated charts
docker/       Backend Dockerfile
```

## Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

The API runs at `http://localhost:5000`.

Available endpoints:

- `GET /`
- `GET /slots`
- `GET /metrics`
- `POST /allocate`

## Frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard runs at `http://localhost:5173`.

## Train The RL Agent

```bash
python rl/train.py
```

Outputs:

- `models/q_policy.pkl`
- `experiments/training_rewards.csv`

## Evaluate

```bash
python compare.py
python plot_rewards.py
```

Outputs:

- `experiments/evaluation_summary.json`
- `experiments/comparison_rewards.csv`
- `plots/training_rewards.png`

## Docker

```bash
docker compose up --build
```
