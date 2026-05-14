import time
from copy import deepcopy

try:
    from ..engine.congestionEngine import CongestionEngine
    from ..engine.pathfinding import AStarPathfinder
    from .allocator import SmartSlotAllocator
    from .environment import ParkingEnvironment
    from .stateEncoder import StateEncoder
except ImportError:
    from engine.congestionEngine import CongestionEngine
    from engine.pathfinding import AStarPathfinder
    from rl.allocator import SmartSlotAllocator
    from rl.environment import ParkingEnvironment
    from rl.stateEncoder import StateEncoder


class ParkingAllocator:
    """Runtime simulation facade used by Flask routes.

    The class preserves the old API surface while changing the model from a
    linear slot list to spatial allocation with paths, zone balance and
    DQN-ready state observations.
    """

    def __init__(self):
        self.environment = ParkingEnvironment()
        self.layout = self.environment.get_layout()
        self.pathfinder = AStarPathfinder(self.layout)
        self.congestion_engine = CongestionEngine(self.layout["zones"])
        self.smart_allocator = SmartSlotAllocator(self.pathfinder)
        self.state_encoder = StateEncoder()
        self.total_requests = 0
        self.successful_allocations = 0
        self.next_car_number = 1
        self.cars_processed = 0
        self.waiting_queue = []
        self.moving_vehicles = []

    def get_layout(self):
        layout = self.environment.get_layout()
        layout["zones"] = self._zones_with_heat()
        return layout

    def get_slots(self):
        return self.environment.get_slots()

    def get_zone_stats(self):
        return self.congestion_engine.calculate(self.environment.get_slots(), self.moving_vehicles)

    def get_moving_vehicles(self):
        self._refresh_vehicle_positions()
        return deepcopy(self.moving_vehicles)

    def get_state(self):
        return {
            "layout": self.get_layout(),
            "slots": self.get_slots(),
            "metrics": self.get_metrics(),
            "zone_stats": self.get_zone_stats(),
            "moving_vehicles": self.get_moving_vehicles(),
            "waiting_queue": list(self.waiting_queue),
        }

    def get_metrics(self):
        slots = self.environment.get_slots()
        occupied = sum(1 for slot in slots if slot["occupied"])
        total = len(slots)
        free = total - occupied
        occupancy_percentage = (occupied / total) * 100 if total else 0
        return {
            "total_slots": total,
            "occupied_slots": occupied,
            "free_slots": free,
            "cars_processed": self.cars_processed,
            "successful_allocations": self.successful_allocations,
            "occupancy_percentage": round(occupancy_percentage, 2),
            "waiting_queue_length": len(self.waiting_queue),
            "moving_vehicles": len(self.moving_vehicles),
        }

    def enqueue(self):
        car_id = self._next_car_id()
        self.waiting_queue.append(car_id)
        self.total_requests += 1
        return {
            "enqueued": True,
            "message": f"Car {car_id} added to waiting queue.",
            "car_id": car_id,
            "waiting_queue_length": len(self.waiting_queue),
            "metrics": self.get_metrics(),
            "state": self.get_state(),
        }

    def allocate(self):
        self._refresh_vehicle_positions()
        if not self.waiting_queue:
            return {
                "allocated": False,
                "message": "No incoming cars in the waiting queue.",
                "slot": None,
                "metrics": self.get_metrics(),
                "state": self.get_state(),
            }

        free_slots = self.environment.free_slots()
        if not free_slots:
            return {
                "allocated": False,
                "message": "No free parking slots available.",
                "slot": None,
                "metrics": self.get_metrics(),
                "state": self.get_state(),
            }

        car_id = self.waiting_queue.pop(0)
        zone_stats = self.get_zone_stats()
        candidate = self.smart_allocator.choose_slot(free_slots, zone_stats)
        slot = self.environment.occupy(candidate["slot"]["id"], car_id)
        vehicle = self._create_vehicle(car_id, slot, candidate)
        self.moving_vehicles.append(vehicle)
        self.cars_processed += 1
        self.successful_allocations += 1

        return {
            "allocated": True,
            "message": f"Car {car_id} assigned to slot {slot['id']} via Zone {slot['zone']}.",
            "slot": slot,
            "path": vehicle["path"],
            "vehicle": vehicle,
            "score": candidate["score"],
            "reward": candidate["reward"],
            "metrics": self.get_metrics(),
            "state": self.get_state(),
        }

    def remove(self, slot_id):
        slot = self.environment.find_slot(slot_id)
        if slot is None:
            return {
                "removed": False,
                "message": "A valid spatial slot_id is required, for example A1 or C4.",
                "slot": None,
                "metrics": self.get_metrics(),
                "state": self.get_state(),
            }

        if not slot["occupied"]:
            return {
                "removed": False,
                "message": f"Slot {slot['id']} is already free.",
                "slot": deepcopy(slot),
                "metrics": self.get_metrics(),
                "state": self.get_state(),
            }

        removed_car_id = slot.get("car_id")
        released = self.environment.release(slot["id"])
        self.moving_vehicles = [
            vehicle for vehicle in self.moving_vehicles if vehicle["car_id"] != removed_car_id
        ]
        return {
            "removed": True,
            "message": f"Car {removed_car_id} removed from slot {released['id']}.",
            "slot": released,
            "metrics": self.get_metrics(),
            "state": self.get_state(),
        }

    def dqn_observation(self):
        observation = self.environment.observe(self.get_zone_stats(), self.layout["entry"])
        return {
            "observation": observation,
            "encoded_state": self.state_encoder.encode(observation),
            "actions": observation["available_actions"],
        }

    def _create_vehicle(self, car_id, slot, candidate):
        now = time.time()
        return {
            "car_id": car_id,
            "slot_id": slot["id"],
            "zone": slot["zone"],
            "path": candidate["path"],
            "path_length": candidate["path_length"],
            "score": candidate["score"],
            "reward": candidate["reward"],
            "started_at": now,
            "duration": max(3.0, candidate["path_length"] / 90),
            "status": "moving",
            "position": candidate["path"][0],
        }

    def _refresh_vehicle_positions(self):
        now = time.time()
        for vehicle in self.moving_vehicles:
            elapsed = now - vehicle["started_at"]
            progress = min(1, elapsed / vehicle["duration"])
            vehicle["position"] = self._interpolate(vehicle["path"], progress)
            vehicle["progress"] = round(progress, 3)
            vehicle["status"] = "parked" if progress >= 1 else "moving"

    def _interpolate(self, path, progress):
        if progress >= 1:
            return path[-1]
        segment_count = len(path) - 1
        segment_position = progress * segment_count
        index = int(segment_position)
        local_progress = segment_position - index
        start = path[index]
        end = path[index + 1]
        return {
            "x": round(start["x"] + (end["x"] - start["x"]) * local_progress, 2),
            "y": round(start["y"] + (end["y"] - start["y"]) * local_progress, 2),
        }

    def _zones_with_heat(self):
        zone_stats = self.get_zone_stats()
        zones = []
        for zone in self.layout["zones"]:
            next_zone = deepcopy(zone)
            next_zone["congestion"] = zone_stats.get(zone["id"], {}).get("congestion_score", 0)
            zones.append(next_zone)
        return zones

    def _next_car_id(self):
        car_id = f"CAR-{self.next_car_number:03d}"
        self.next_car_number += 1
        return car_id
