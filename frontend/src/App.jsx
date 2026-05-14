import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { io } from "socket.io-client";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:5001";
const SOCKET_URL = import.meta.env.VITE_SOCKET_URL ?? API_URL;

function App() {
  const [state, setState] = useState(null);
  const [status, setStatus] = useState("Connecting to simulation");
  const [manualSlotId, setManualSlotId] = useState("");
  const [lastAssignment, setLastAssignment] = useState(null);

  const loadDashboard = useCallback(async () => {
    try {
      const response = await fetch(`${API_URL}/state`);
      const data = await response.json();
      setState(data);
      setStatus("Simulation online");
    } catch (error) {
      setStatus("Backend is not reachable on port 5001");
    }
  }, []);

  useEffect(() => {
    loadDashboard();
    const socket = io(SOCKET_URL, { transports: ["websocket", "polling"] });
    socket.on("parking_state", (payload) => {
      setState(payload);
      setStatus("Realtime update received");
    });
    socket.on("connect", () => setStatus("Socket.IO connected"));
    socket.on("disconnect", () => setStatus("Socket.IO disconnected, polling fallback active"));

    const interval = window.setInterval(loadDashboard, 1400);
    return () => {
      socket.disconnect();
      window.clearInterval(interval);
    };
  }, [loadDashboard]);

  async function postAction(endpoint, options) {
    const response = await fetch(`${API_URL}${endpoint}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    const data = await response.json();
    setStatus(data.message ?? "Action complete");
    if (data.allocated) {
      setLastAssignment({
        carId: data.vehicle.car_id,
        slotId: data.slot.id,
        zone: data.slot.zone,
        score: data.score,
        reward: data.reward,
      });
    }
    if (data.state) {
      setState(data.state);
    } else {
      await loadDashboard();
    }
  }

  function enqueueCar() {
    setStatus("Adding vehicle to entry queue");
    postAction("/enqueue");
  }

  function allocateCar() {
    setStatus("Scoring spatial slots");
    postAction("/allocate");
  }

  async function startSimulation() {
    setStatus("Starting automatic simulation");
    await postAction("/simulation/start");
  }

  async function stopSimulation() {
    setStatus("Stopping automatic simulation");
    await postAction("/simulation/stop");
  }

  function removeCar(slotId) {
    setStatus(`Removing vehicle from ${slotId}`);
    postAction("/remove", { body: JSON.stringify({ slot_id: slotId }) });
  }

  function handleManualRemove(event) {
    event.preventDefault();
    if (!manualSlotId) return;
    removeCar(manualSlotId);
    setManualSlotId("");
  }

  const metrics = state?.metrics;
  const zoneStats = state?.zone_stats ?? {};
  const slotsByZone = useMemo(() => {
    return (state?.slots ?? []).reduce((groups, slot) => {
      groups[slot.zone] = groups[slot.zone] || [];
      groups[slot.zone].push(slot);
      return groups;
    }, {});
  }, [state]);

  return (
    <main className="dashboard">
      <section className="topbar">
        <div>
          <p className="eyebrow">Spatial Smart Parking Simulation</p>
          <h1>RL-SmartParking Control</h1>
        </div>
        <div className="actions">
          <button className="btn" onClick={startSimulation}>
            Start Simulation
          </button>
          <button className="btn danger" onClick={stopSimulation}>
            Stop Simulation
          </button>
          <button className="btn ghost" onClick={loadDashboard}>Refresh</button>
          <button className="btn" onClick={enqueueCar}>Add Vehicle</button>
          <button
            className="btn primary"
            onClick={allocateCar}
            disabled={!metrics?.waiting_queue_length || !metrics?.free_slots}
          >
            Allocate Smart Slot
          </button>
        </div>
      </section>

      <section className="metrics">
        <Metric label="Available" value={metrics?.free_slots ?? 0} />
        <Metric label="Parked" value={metrics?.parked_vehicles ?? 0} />
        <Metric label="Moving" value={metrics?.moving_vehicles ?? 0} />
        <Metric label="Queue" value={metrics?.waiting_queue_length ?? 0} accent />
        <Metric label="Occupancy" value={`${metrics?.occupancy_percentage ?? 0}%`} />
        <Metric label="Throughput" value={metrics?.throughput ?? 0} />
      </section>

      <section className="control-grid">
        <div className="map-panel">
          <div className="panel-heading">
            <div>
              <h2>Single-Floor Spatial Map</h2>
              <p>{status}</p>
            </div>
            {lastAssignment && (
              <span className="assignment">
                {lastAssignment.carId} to {lastAssignment.slotId} | score {lastAssignment.score}
              </span>
            )}
          </div>
          <ParkingCanvas state={state} onRemove={removeCar} />
        </div>

        <aside className="side-panel">
          <form className="remove-form" onSubmit={handleManualRemove}>
            <label htmlFor="slotId">Release slot</label>
            <div>
              <input
                id="slotId"
                value={manualSlotId}
                placeholder="A1"
                onChange={(event) => setManualSlotId(event.target.value.toUpperCase())}
              />
              <button className="btn danger" disabled={!manualSlotId}>Release</button>
            </div>
          </form>

          <h2>Zone Balance</h2>
          <div className="zone-list">
            {["A", "B", "C"].map((zoneId) => (
              <ZoneCard
                key={zoneId}
                zoneId={zoneId}
                stats={zoneStats[zoneId]}
                slots={slotsByZone[zoneId] ?? []}
              />
            ))}
          </div>
        </aside>
      </section>
    </main>
  );
}

function ParkingCanvas({ state, onRemove }) {
  const canvasRef = useRef(null);
  const hitZonesRef = useRef([]);

  useEffect(() => {
    if (!state?.layout || !canvasRef.current) return;
    let animationFrame;
    const canvas = canvasRef.current;
    const context = canvas.getContext("2d");

    function draw() {
      const rect = canvas.getBoundingClientRect();
      const scale = Math.min(rect.width / state.layout.width, rect.height / state.layout.height);
      const offsetX = (rect.width - state.layout.width * scale) / 2;
      const offsetY = (rect.height - state.layout.height * scale) / 2;
      canvas.width = rect.width * window.devicePixelRatio;
      canvas.height = rect.height * window.devicePixelRatio;
      context.setTransform(window.devicePixelRatio, 0, 0, window.devicePixelRatio, 0, 0);
      context.clearRect(0, 0, rect.width, rect.height);
      context.fillStyle = "#17201b";
      context.fillRect(0, 0, rect.width, rect.height);

      const project = (point) => ({
        x: offsetX + point.x * scale,
        y: offsetY + point.y * scale,
      });

      drawZones(context, state.layout.zones, scale, offsetX, offsetY);
      drawRoads(context, state.layout.roads, state.layout.lanes, scale, offsetX, offsetY);
      hitZonesRef.current = drawSlots(context, state.slots, project, onRemove);
      drawEntryExit(context, state.layout.entry, state.layout.exit, project);
      drawVehicles(context, state.moving_vehicles, project);
      animationFrame = window.requestAnimationFrame(draw);
    }

    draw();
    return () => window.cancelAnimationFrame(animationFrame);
  }, [state, onRemove]);

  function handleClick(event) {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;
    const target = hitZonesRef.current.find((slot) => (
      x >= slot.x && x <= slot.x + slot.width && y >= slot.y && y <= slot.y + slot.height
    ));
    if (target?.occupied) {
      onRemove(target.id);
    }
  }

  return <canvas ref={canvasRef} className="parking-canvas" onClick={handleClick} />;
}

function drawZones(context, zones, scale, offsetX, offsetY) {
  zones.forEach((zone) => {
    const heat = Math.min(1, Math.max(0, zone.congestion ?? 0));
    const red = Math.round(72 + heat * 168);
    const green = Math.round(146 - heat * 60);
    context.fillStyle = `rgba(${red}, ${green}, 74, ${0.12 + heat * 0.24})`;
    context.strokeStyle = `rgba(${red}, ${green + 45}, 95, 0.72)`;
    context.lineWidth = 2;
    context.fillRect(offsetX + zone.x * scale, offsetY + zone.y * scale, zone.width * scale, zone.height * scale);
    context.strokeRect(offsetX + zone.x * scale, offsetY + zone.y * scale, zone.width * scale, zone.height * scale);
    context.fillStyle = "#eef6e8";
    context.font = "700 14px Inter, sans-serif";
    context.fillText(zone.label, offsetX + (zone.x + 14) * scale, offsetY + (zone.y + 24) * scale);
  });
}

function drawRoads(context, roads, lanes, scale, offsetX, offsetY) {
  roads.forEach((road) => {
    context.fillStyle = "#2f3430";
    context.fillRect(offsetX + road.x * scale, offsetY + road.y * scale, road.width * scale, road.height * scale);
  });
  context.strokeStyle = "#d7c66f";
  context.setLineDash([14, 14]);
  context.lineWidth = 2;
  lanes.forEach((lane) => {
    context.beginPath();
    lane.points.forEach((point, index) => {
      const x = offsetX + point.x * scale;
      const y = offsetY + point.y * scale;
      index === 0 ? context.moveTo(x, y) : context.lineTo(x, y);
    });
    context.stroke();
  });
  context.setLineDash([]);
}

function drawSlots(context, slots, project) {
  return slots.map((slot) => {
    const point = project(slot);
    const width = 46;
    const height = 58;
    const x = point.x - width / 2;
    const y = point.y - height / 2;
    let fillColor = "#5a8f63";
    let strokeColor = "#d7f4d1";
    const status = slot.status ?? (slot.occupied ? "occupied" : "available");
    if (status === "reserved") {
      fillColor = "#eab308";
      strokeColor = "#fff3bf";
    }

    else if (status === "occupied") {
      fillColor = "#ef4444";
      strokeColor = "#ffd0cb";
    }

    context.fillStyle = fillColor;
    context.strokeStyle = strokeColor;
    context.lineWidth = 2;
    context.fillRect(x, y, width, height);
    context.strokeRect(x, y, width, height);
    context.fillStyle = "#f8fbf4";
    context.font = "700 12px Inter, sans-serif";
    context.fillText(slot.id, x + 10, y + 18);
    if (status !== "available") {
      context.fillStyle = "#2a1718";
      context.fillRect(x + 9, y + 28, 28, 18);
    }
    return {
      id: slot.id,
      occupied: status !== "available",
      x,
      y,
      width,
      height
    };
  });
}

function drawEntryExit(context, entry, exit, project) {
  [
    { point: entry, label: "ENTRY", color: "#8cc56e" },
    { point: exit, label: "EXIT", color: "#d48b5f" },
  ].forEach((marker) => {
    const point = project(marker.point);
    context.fillStyle = marker.color;
    context.beginPath();
    context.arc(point.x, point.y, 10, 0, Math.PI * 2);
    context.fill();
    context.fillStyle = "#f8fbf4";
    context.font = "700 11px Inter, sans-serif";
    context.fillText(marker.label, point.x - 18, point.y - 16);
  });
}

function drawVehicles(context, vehicles, project) {
  vehicles.forEach((vehicle) => {
    const point = project(vehicle.position);
    context.fillStyle = vehicle.status === "parked" ? "#f1c75b" : "#4aa3a2";
    context.beginPath();
    context.roundRect(point.x - 13, point.y - 8, 26, 16, 5);
    context.fill();
    context.fillStyle = "#0e1715";
    context.fillRect(point.x - 6, point.y - 5, 12, 10);
  });
}

function ZoneCard({ zoneId, stats, slots }) {
  const congestion = stats?.congestion_score ?? 0;
  return (
    <article className="zone-card">
      <div className="zone-card-heading">
        <strong>Zone {zoneId}</strong>
        <span>{Math.round(congestion * 100)} congestion</span>
      </div>
      <div className="bar">
        <span style={{ width: `${stats?.occupancy_percentage ?? 0}%` }} />
      </div>
      <p>
        {stats?.available_slots ?? 0} free of {stats?.total_slots ?? slots.length}
        <br />
        {stats?.reserved_slots ?? 0} reserved | {stats?.moving_vehicles ?? 0} moving
      </p>
    </article>
  );
}

function Metric({ label, value, accent }) {
  return (
    <article className={`metric ${accent ? "accent" : ""}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

export default App;
