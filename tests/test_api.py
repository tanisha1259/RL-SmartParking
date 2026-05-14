import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app import create_app  # noqa: E402


def test_api_health_and_metrics():
    app = create_app()
    client = app.test_client()

    assert client.get("/").status_code == 200
    metrics = client.get("/metrics")

    assert metrics.status_code == 200
    assert "free_slots" in metrics.get_json()


def test_enqueue_allocate_remove_flow():
    app = create_app()
    client = app.test_client()

    enqueue = client.post("/enqueue")
    assert enqueue.status_code == 200

    allocation = client.post("/allocate")
    assert allocation.status_code == 200
    allocated = allocation.get_json()
    assert allocated["allocated"] is True
    assert allocated["slot"]["status"] == "reserved"
    assert allocated["slot"]["occupied"] is True

    removal = client.post("/remove", json={"slot_id": allocated["slot"]["id"]})
    assert removal.status_code == 200
    released = removal.get_json()["slot"]
    assert released["status"] == "available"
    assert released["occupied"] is False
