from backend.rl.inference import ParkingAllocator


def test_reservation_and_occupied_status_stay_compatible():
    allocator = ParkingAllocator()
    allocator.enqueue()

    result = allocator.allocate()

    assert result["allocated"] is True
    slot = result["slot"]
    assert slot["status"] == "reserved"
    assert slot["occupied"] is True

    allocator.moving_vehicles[0]["started_at"] -= allocator.moving_vehicles[0]["duration"] + 1
    vehicles = allocator.get_moving_vehicles()
    parked_slot = allocator.environment.find_slot(vehicles[0]["slot_id"])

    assert vehicles[0]["status"] == "parked"
    assert parked_slot["status"] == "occupied"
    assert parked_slot["occupied"] is True


def test_release_restores_available_and_occupied_false():
    allocator = ParkingAllocator()
    allocator.enqueue()
    result = allocator.allocate()

    released = allocator.remove(result["slot"]["id"])

    assert released["removed"] is True
    assert released["slot"]["status"] == "available"
    assert released["slot"]["occupied"] is False


def test_congestion_engine_handles_moving_vehicles():
    allocator = ParkingAllocator()
    allocator.enqueue()
    allocator.allocate()

    stats = allocator.get_zone_stats()

    assert set(stats) == {"A", "B", "C"}
    assert all("congestion_score" in zone for zone in stats.values())
