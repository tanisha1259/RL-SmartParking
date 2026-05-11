from flask import Blueprint, jsonify, request

try:
    from ..rl.inference import ParkingAllocator
except ImportError:
    from rl.inference import ParkingAllocator

api_bp = Blueprint("api", __name__)
allocator = ParkingAllocator()


@api_bp.get("/")
def home():
    return jsonify(
        {
            "message": "RL Smart Parking API",
            "endpoints": {
                "GET /": "API health and endpoint list",
                "GET /slots": "Current parking slot state",
                "GET /metrics": "Current parking metrics",
                "POST /allocate": "Allocate the nearest free slot",
                "POST /remove": "Remove a car from a slot",
            },
        }
    )


@api_bp.get("/slots")
def slots():
    return jsonify({"slots": allocator.get_slots()})


@api_bp.get("/metrics")
def metrics():
    return jsonify(allocator.get_metrics())


@api_bp.post("/enqueue")
def enqueue():
    result = allocator.enqueue()
    return jsonify(result), 200

@api_bp.post("/allocate")
def allocate():
    result = allocator.allocate()
    status_code = 200 if result["allocated"] else 409
    return jsonify(result), status_code


@api_bp.post("/remove")
def remove():
    data = request.get_json(silent=True) or {}
    result = allocator.remove(slot_id=data.get("slot_id"))
    status_code = 200 if result["removed"] else 400
    return jsonify(result), status_code
