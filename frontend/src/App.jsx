import { useEffect, useState } from "react";

const API_URL = "http://localhost:5000";

function App() {
  const [slots, setSlots] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [status, setStatus] = useState("Ready");

  async function loadDashboard() {
    const [slotsResponse, metricsResponse] = await Promise.all([
      fetch(`${API_URL}/slots`),
      fetch(`${API_URL}/metrics`),
    ]);

    const slotsData = await slotsResponse.json();
    const metricsData = await metricsResponse.json();
    setSlots(slotsData.slots);
    setMetrics(metricsData);
  }

  async function allocateCar() {
    setStatus("Allocating...");
    const response = await fetch(`${API_URL}/allocate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ car_id: `CAR-${Date.now()}` }),
    });
    const data = await response.json();
    setStatus(data.message);
    await loadDashboard();
  }

  useEffect(() => {
    loadDashboard().catch(() => {
      setStatus("Backend is not reachable. Start Flask on port 5000.");
    });
  }, []);

  return (
    <main className="dashboard">
      <section className="topbar">
        <div>
          <p className="eyebrow">Smart Parking Allocation</p>
          <h1>RL-SmartParking</h1>
        </div>
        <button onClick={allocateCar}>Allocate Car</button>
      </section>

      <section className="metrics">
        <Metric label="Total Slots" value={metrics?.total_slots ?? 0} />
        <Metric label="Free Slots" value={metrics?.free_slots ?? 0} />
        <Metric label="Occupied" value={metrics?.occupied_slots ?? 0} />
        <Metric
          label="Occupancy"
          value={`${metrics?.occupancy_percentage ?? 0}%`}
        />
      </section>

      <section className="parking-panel">
        <div className="panel-heading">
          <h2>Parking Slots</h2>
          <span>{status}</span>
        </div>
        <div className="slot-grid">
          {slots.map((slot) => (
            <article
              key={slot.id}
              className={`slot ${slot.occupied ? "occupied" : "free"}`}
            >
              <strong>Slot {slot.id}</strong>
              <span>{slot.occupied ? slot.car_id : "Free"}</span>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

function Metric({ label, value }) {
  return (
    <article className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

export default App;
