# Smart Parking Allocation - Final Report

## 1. Problem Statement
Urban parking facilities often suffer from inefficient space utilization, causing incoming vehicles to spend excessive time searching for slots. This leads to long queues, congestion, and increased emissions. **Goal:** Control parking slot allocation using Reinforcement Learning to reduce average waiting time and balance zone occupancy inside the facility.

## 2. SDG Impact (SDG 11: Sustainable Cities and Communities)
By dynamically routing cars to specific parking zones instead of allowing random searches, this project reduces the time vehicles spend idling or driving around inside the structure. Reducing average wait-time and eliminating "hunting" for spots supports **SDG 11** by directly reducing urban congestion, fuel waste, and local air pollution.

## 3. The Simulator
The `sim/parking_env.py` acts as the environment. 
- **Arrivals & Departures:** Simulates cars arriving at random intervals based on traffic pressure and departing based on a probability curve.
- **Queuing:** Unallocated cars wait in a queue. If the queue length exceeds the maximum capacity, incoming cars are "rejected" (turned away from the garage).

## 4. Reinforcement Learning Methodology
- **Algorithm Choice:** We used **Q-Learning** because the state space (discrete queue lengths, discrete traffic buckets, and binary occupancy of 12 slots) is relatively small and finite, allowing tabular Q-learning to converge reliably without the overhead of deep neural networks.
- **State Representation:** 
  1. `Available parking slots`: A tuple of 1s (occupied) and 0s (free).
  2. `Incoming cars`: The current length of the waiting queue.
  3. `Occupancy levels`: The global traffic intensity bucket (1, 2, or 3).
- **Action:** An integer representing the slot index to allocate the next waiting car to.
- **Reward Structure:**
  - *Reduced search time*: Distance penalty for assigning distant slots.
  - *Reduced congestion*: Bonus for taking cars out of the waiting queue.
  - *Efficient utilization*: Bonus for maintaining balanced occupancy across physical zones.
- **Exploration Strategy:** Epsilon-greedy strategy, starting at 1.0 (pure exploration) and decaying down to 0.03 over 800-1000 episodes to prioritize exploitation.

## 5. MLOps Implementation
- **Configuration Management:** Hyperparameters are decoupled from the code into `configs/` directory.
- **Experiment Tracking:** The `train.py` script generates a unique `run-id` (e.g., `run_3e792c99`) for each experiment. It saves hyperparameter configurations (`training_summary_run_xxxx.json`) and specific run metrics (`rewards_run_xxxx.csv`) to perfectly track which model version produced which result.
- **Reproducibility:** A colleague can clone the repository and run `python rl/train.py --config configs/qlearning_v1.yaml` to perfectly recreate `policy_v1.pkl`.
- **Monitoring Plan (If Deployed):**
  - We would track average wait-time, maximum queue length, and zone balancing. 
  - If the average wait-time metric spikes significantly beyond the simulated baseline (indicating a shift in real-world traffic behavior), a data drift alert would trigger a pipeline to retrain the Q-table.

## 6. Results and Analysis
**Fixed-Timer (Linear Allocation) vs RL-Policy:**
The RL-policy consistently outperforms naive nearest-free-slot allocation because the RL agent strategically leaves nearby slots open when traffic pressure is low, anticipating sudden spikes in the queue. 
- **When it performs best:** During high traffic pressure with long queues, the RL agent quickly identifies the most efficient zones to distribute the queue into, earning the queue relief bonus.
- **When it behaves badly:** During pure exploration phases (high epsilon), the agent may assign slots at the extreme back of the lot, incurring massive distance penalties.
- **Sensitivity:** The model is highly sensitive to the `target_occupancy` hyperparameter. If traffic exceeds this threshold heavily, the zone balancing penalty outweighs the queue relief bonus, confusing the agent temporarily.

## 7. Limitations
- Tabular Q-learning cannot scale to hundreds of slots (the state space explodes). A Deep Q-Network (DQN) would be required for a full-scale mega-structure.
