import { useEffect, useState } from "react";

const API_URL = "http://localhost:5001";

function App() {
  const [slots, setSlots] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [status, setStatus] = useState("Ready");
  const [manualSlotId, setManualSlotId] = useState("");

  async function loadDashboard() {
    try {
      const [slotsResponse, metricsResponse] = await Promise.all([
        fetch(`${API_URL}/slots`),
        fetch(`${API_URL}/metrics`),
      ]);

      const slotsData = await slotsResponse.json();
      const metricsData = await metricsResponse.json();
      setSlots(slotsData.slots);
      setMetrics(metricsData);
    } catch (error) {
      setStatus("Backend is not reachable. Ensure Flask is running on port 5001.");
    }
  }

  async function enqueueCar() {
    setStatus("Adding car to waiting queue...");
    const response = await fetch(`${API_URL}/enqueue`, {
      method: "POST",
    });
    const data = await response.json();
    setStatus(data.message);
    await loadDashboard();
  }

  async function allocateCar() {
    if (metrics?.waiting_queue_length === 0) {
      setStatus("No cars in waiting queue to allocate!");
      return;
    }
    setStatus("Allocating car from queue...");
    const response = await fetch(`${API_URL}/allocate`, {
      method: "POST",
    });
    const data = await response.json();
    setStatus(data.message);
    await loadDashboard();
  }

  async function removeCar(slotId) {
    setStatus(`Removing car from slot ${slotId}...`);
    const response = await fetch(`${API_URL}/remove`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slot_id: slotId }),
    });
    const data = await response.json();
    setStatus(data.message);
    await loadDashboard();
  }

  function handleManualRemove(e) {
    e.preventDefault();
    if (manualSlotId) {
      removeCar(manualSlotId);
      setManualSlotId("");
    }
  }

  useEffect(() => {
    loadDashboard();
  }, []);

  const topRow = slots.slice(0, 6);
  const bottomRow = slots.slice(6, 12);

  return (
    <main className="dashboard">
      <div className="glass-bg"></div>
      
      <section className="topbar">
        <div className="title-area">
          <p className="eyebrow">Smart Parking Allocation</p>
          <h1>RL-SmartParking</h1>
        </div>
        <div className="action-area">
          <form className="manual-remove" onSubmit={handleManualRemove}>
            <input 
              type="text" 
              placeholder="Slot ID" 
              value={manualSlotId} 
              onChange={(e) => setManualSlotId(e.target.value)}
            />
            <button type="submit" className="btn-secondary" disabled={!manualSlotId}>Delocate</button>
          </form>
          <div className="queue-actions">
            <button className="btn-accent" onClick={enqueueCar}>Add to Queue</button>
            <button className="btn-primary" onClick={allocateCar} disabled={metrics?.waiting_queue_length === 0}>
              Allocate Car
            </button>
          </div>
        </div>
      </section>

      <section className="metrics">
        <Metric label="Total Slots" value={metrics?.total_slots ?? 0} icon="🅿️" />
        <Metric label="Free Slots" value={metrics?.free_slots ?? 0} icon="✨" />
        <Metric label="Occupied" value={metrics?.occupied_slots ?? 0} icon="🚗" />
        <Metric label="Occupancy" value={`${metrics?.occupancy_percentage ?? 0}%`} icon="📊" />
        <Metric 
          label="Waiting Queue" 
          value={metrics?.waiting_queue_length ?? 0} 
          icon="🚦" 
          highlight={metrics?.waiting_queue_length > 0} 
        />
      </section>

      <section className="parking-panel glass-panel">
        <div className="panel-heading">
          <h2>Parking Layout</h2>
          <span className="status-indicator">{status}</span>
        </div>
        
        <div className="parking-lot">
          {/* Top Row */}
          <div className="slot-row top-row">
            {topRow.map((slot) => (
              <ParkingSlot key={slot.id} slot={slot} onRemove={() => removeCar(slot.id)} />
            ))}
          </div>

          {/* Road Visual */}
          <div className="road">
            <div className="road-lines"></div>
            {metrics?.waiting_queue_length > 0 && (
              <div className="waiting-cars-visual">
                {Array.from({ length: Math.min(metrics.waiting_queue_length, 5) }).map((_, i) => (
                  <div key={i} className="waiting-car-icon">🏎️</div>
                ))}
                {metrics.waiting_queue_length > 5 && <span className="more-cars">+{metrics.waiting_queue_length - 5} more</span>}
              </div>
            )}
          </div>

          {/* Bottom Row */}
          <div className="slot-row bottom-row">
            {bottomRow.map((slot) => (
              <ParkingSlot key={slot.id} slot={slot} onRemove={() => removeCar(slot.id)} />
            ))}
          </div>
        </div>
      </section>
    </main>
  );
}

function ParkingSlot({ slot, onRemove }) {
  return (
    <article
      onClick={() => slot.occupied && onRemove()}
      className={`slot ${slot.occupied ? "occupied" : "free"} ${slot.occupied ? "clickable" : ""}`}
      title={slot.occupied ? "Click to delocate" : ""}
    >
      <div className="slot-header">
        <strong>{slot.id}</strong>
        {slot.occupied && <span className="remove-icon">×</span>}
      </div>
      <span className="car-id">{slot.occupied ? slot.car_id : "Free"}</span>
      <div className="slot-glow"></div>
    </article>
  );
}

function Metric({ label, value, icon, highlight }) {
  return (
    <article className={`metric glass-panel ${highlight ? "highlight" : ""}`}>
      <div className="metric-icon">{icon}</div>
      <div className="metric-data">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </article>
  );
}

export default App;
