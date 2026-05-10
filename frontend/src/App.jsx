import { useEffect, useMemo, useState } from "react";

const API_URL = "http://localhost:5000";

function App() {
  const [slots, setSlots] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [notification, setNotification] = useState({
    type: "info",
    message: "Loading parking dashboard...",
  });
  const [isBusy, setIsBusy] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const occupancy = useMemo(() => {
    if (!metrics?.total_slots) {
      return 0;
    }

    return Math.round((metrics.occupied_slots / metrics.total_slots) * 100);
  }, [metrics]);

  async function requestJson(path, options) {
    const response = await fetch(`${API_URL}${path}`, options);
    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      throw new Error(data.message || "Something went wrong.");
    }

    return data;
  }

  async function loadDashboard() {
    const [slotsData, metricsData] = await Promise.all([
      requestJson("/slots"),
      requestJson("/metrics"),
    ]);

    setSlots(slotsData.slots ?? []);
    setMetrics(metricsData);
  }

  async function refreshDashboard(message, type = "success") {
    await loadDashboard();
    setNotification({ type, message });
  }

  async function allocateCar() {
    setIsBusy(true);

    try {
      const data = await requestJson("/allocate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ car_id: `CAR-${Date.now().toString().slice(-5)}` }),
      });

      const slotLabel = data.slot ? `Slot ${data.slot.id + 1}` : "a slot";
      await refreshDashboard(`Slot allocated: ${slotLabel}`, "success");
    } catch (error) {
      await refreshDashboard(
        error.message.includes("No free") ? "Parking full" : error.message,
        "warning",
      );
    } finally {
      setIsBusy(false);
    }
  }

  async function removeCar() {
    setIsBusy(true);

    try {
      const data = await requestJson("/remove", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      const slotLabel = data.slot ? `Slot ${data.slot.id + 1}` : "A slot";
      await refreshDashboard(`Slot freed: ${slotLabel}`, "success");
    } catch (error) {
      await refreshDashboard(error.message, "warning");
    } finally {
      setIsBusy(false);
    }
  }

  useEffect(() => {
    loadDashboard()
      .then(() => {
        setNotification({
          type: "success",
          message: "Dashboard connected to the parking API.",
        });
      })
      .catch(() => {
        setNotification({
          type: "error",
          message: "Backend is not reachable. Start Flask on port 5000.",
        });
      })
      .finally(() => {
        setIsLoading(false);
      });
  }, []);

  return (
    <main className="dashboard">
      <section className="hero">
        <div>
          <p className="eyebrow">Reinforcement learning parking control</p>
          <h1>RL-SmartParking Dashboard</h1>
          <p className="intro">
            Track slot availability in real time and let the allocator choose
            the next best parking space.
          </p>
        </div>

        <div className="actions" aria-label="Parking actions">
          <button onClick={allocateCar} disabled={isBusy || isLoading}>
            Allocate Car
          </button>
          <button
            className="secondary"
            onClick={removeCar}
            disabled={isBusy || isLoading || !metrics?.occupied_slots}
          >
            Remove Car
          </button>
        </div>
      </section>

      <section className="status-row" aria-live="polite">
        <div className={`notification ${notification.type}`}>
          <span className="notification-dot" />
          {notification.message}
        </div>
        <div className="api-status">
          <span className={metrics ? "online" : "offline"} />
          {metrics ? "API online" : "Waiting for API"}
        </div>
      </section>

      <section className="metrics" aria-label="Parking metrics">
        <Metric label="Total Slots" value={metrics?.total_slots ?? 0} />
        <Metric label="Occupied Slots" value={metrics?.occupied_slots ?? 0} />
        <Metric label="Free Slots" value={metrics?.free_slots ?? 0} />
<<<<<<< HEAD
        <Metric label="Occupancy" value={`${occupancy}%`} accent />
=======
        <Metric label="Occupied" value={metrics?.occupied_slots ?? 0} />
        <Metric
          label="Occupancy"
          value={`${metrics?.occupancy_percentage ?? 0}%`}
        />
>>>>>>> origin/main
      </section>

      <section className="parking-panel">
        <div className="panel-heading">
<<<<<<< HEAD
          <div>
            <p className="eyebrow">Live parking grid</p>
            <h2>Slots</h2>
          </div>
          <div className="legend">
            <span>
              <i className="free-key" /> Free
            </span>
            <span>
              <i className="occupied-key" /> Occupied
            </span>
          </div>
=======
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
>>>>>>> origin/main
        </div>

        {isLoading ? (
          <div className="empty-state">Loading slots...</div>
        ) : (
          <div className="slot-grid">
            {slots.map((slot) => (
              <article
                key={slot.id}
                className={`slot ${slot.occupied ? "occupied" : "free"}`}
              >
                <span className="slot-number">Slot {slot.id + 1}</span>
                <strong>{slot.occupied ? "Occupied" : "Free"}</strong>
                <small>{slot.occupied ? slot.car_id : "Ready for a car"}</small>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}

function Metric({ label, value, accent = false }) {
  return (
    <article className={`metric ${accent ? "accent" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

export default App;
