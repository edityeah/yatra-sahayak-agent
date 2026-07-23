import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
import pytest
from fastapi.testclient import TestClient
from webhook import app
from agent import persistence

KEY = {"X-API-Key": "local-dev-key"}


@pytest.fixture
def client():
    return TestClient(app)


def test_api_requires_key(client):
    assert client.get("/api/drills").status_code == 401


def test_logistics_endpoint(client):
    r = client.get("/api/yatra/pandharpur/logistics", headers=KEY)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list) and data and "service" in data[0]


def test_unknown_yatra_404(client):
    assert client.get("/api/yatra/nope/routes", headers=KEY).status_code == 404


def test_drills_endpoint(client):
    r = client.get("/api/drills", headers=KEY)
    assert r.status_code == 200 and isinstance(r.json(), list)


def test_yatra_meta_endpoint(client):
    r = client.get("/api/yatra/kumbh", headers=KEY)
    assert r.status_code == 200 and "control_room" in r.json()


def test_pass_endpoint(client):
    persistence.reset()
    yid = asyncio.run(persistence.create_registration(
        "u", yatra="pandharpur", name="Asha", phone="", group_name="Dindi 5",
        emergency_contact="", medical_flags=""))
    r = client.get(f"/api/pass/{yid}", headers=KEY)
    assert r.status_code == 200 and r.json()["name"] == "Asha"
    assert client.get("/api/pass/NOPE-0000", headers=KEY).status_code == 404
