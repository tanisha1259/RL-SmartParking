from flask import Blueprint, jsonify, request

from extensions import socketio
from rl.inference import ParkingAllocator

api_bp = Blueprint("api", __name__)
allocator = ParkingAllocator()
motion_updates_running = False
simulation_running = False


@api_bp.get("/")
def home():
    return jsonify(
        {
            "message": "RL Smart Parking API",
            "endpoints": {
                "GET /": "API health and endpoint list",
                "GET /slots": "Current parking slot state",
                "GET /layout": "Spatial layout with roads, lanes, zones and slots",
                "GET /metrics": "Current parking metrics",
                "GET /state": "Full realtime dashboard state",
                "GET /congestion": "Live congestion by zone",
                "GET /dqn/state": "DQN-ready observation and encoded vector",
                "POST /allocate": "Allocate using weighted congestion-aware scoring",
                "POST /remove": "Remove a car from a slot",
                "POST /simulation/start": "Start automatic vehicle arrivals and exits",
                "POST /simulation/stop": "Stop automatic vehicle arrivals",
            },
        }
    )


@api_bp.get("/slots")
def slots():
    return jsonify({"slots": allocator.get_slots()})


@api_bp.get("/layout")
def layout():
    return jsonify(allocator.get_layout())


@api_bp.get("/metrics")
def metrics():
    return jsonify(allocator.get_metrics())


@api_bp.get("/state")
def state():
    return jsonify(allocator.get_state())


@api_bp.get("/congestion")
def congestion():
    return jsonify({"zones": allocator.get_zone_stats()})


@api_bp.get("/vehicles")
def vehicles():
    return jsonify({"vehicles": allocator.get_moving_vehicles()})


@api_bp.get("/dqn/state")
def dqn_state():
    return jsonify(allocator.dqn_observation())


@api_bp.post("/enqueue")
def enqueue():
    result = allocator.enqueue()
    _emit_state()
    return jsonify(result), 200


@api_bp.post("/allocate")
def allocate():
    result = allocator.allocate()
    status_code = 200 if result["allocated"] else 409
    _emit_state()
    if result["allocated"]:
        _start_motion_updates()
    return jsonify(result), status_code


@api_bp.post("/remove")
def remove():
    data = request.get_json(silent=True) or {}
    result = allocator.remove(slot_id=data.get("slot_id"))
    status_code = 200 if result["removed"] else 400
    _emit_state()
    return jsonify(result), status_code

@api_bp.post("/simulation/start")
def start_simulation():
    global simulation_running

    if not simulation_running:
        simulation_running = True

        if socketio:
            socketio.start_background_task(
                _auto_simulation_loop
            )

    return jsonify({
        "running": simulation_running,
        "message": "Automatic simulation started.",
        "state": allocator.get_state(),
    })


@api_bp.post("/simulation/stop")
def stop_simulation():
    global simulation_running

    simulation_running = False

    return jsonify({
        "running": simulation_running,
        "message": "Automatic simulation stopped.",
        "state": allocator.get_state(),
    })

def _emit_state():
    if socketio:
        socketio.emit("parking_state", allocator.get_state())

def _auto_simulation_loop():
    global simulation_running
    while simulation_running:
        socketio.sleep(5)
        allocator.enqueue()
        allocation = allocator.allocate()
        if allocation["allocated"]:
            _start_motion_updates()
        allocator.update_vehicle_lifecycle()
        _emit_state()

def _start_motion_updates():
    global motion_updates_running
    if socketio and not motion_updates_running:
        motion_updates_running = True
        socketio.start_background_task(_motion_update_loop)


def _motion_update_loop():
    global motion_updates_running
    try:
        while motion_updates_running:
            socketio.sleep(0.2)
            _emit_state()
            vehicles = allocator.get_moving_vehicles()
            if not vehicles and not simulation_running:
                break
            if not any(v["status"] == "moving" for v in vehicles) and not simulation_running:
                break
    finally:
        motion_updates_running = False

