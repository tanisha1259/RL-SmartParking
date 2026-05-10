from flask import Blueprint, jsonify, request

from rl.inference import ParkingAllocator

api_bp = Blueprint("api", __name__)
allocator = ParkingAllocator()


@api_bp.get("/")
def home():
    return jsonify(
        {
            "message": "RL Smart Parking API",
            "endpoints": ["/slots", "/metrics", "/allocate"],
        }
    )


@api_bp.get("/slots")
def slots():
    return jsonify({"slots": allocator.get_slots()})


@api_bp.get("/metrics")
def metrics():
    return jsonify(allocator.get_metrics())


@api_bp.post("/allocate")
def allocate():
    data = request.get_json(silent=True) or {}
    car_id = data.get("car_id")
    result = allocator.allocate(car_id=car_id)
    status_code = 200 if result["allocated"] else 409
    return jsonify(result), status_code
