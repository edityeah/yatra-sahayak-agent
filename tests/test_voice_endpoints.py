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


def test_token_requires_key(client):
    assert client.post("/api/voice/token", json={"user_id": "u"}).status_code == 401


def test_token_503_when_voice_not_configured(client):
    # No LIVEKIT_* set in this env → voice disabled → 503 (not a crash).
    r = client.post("/api/voice/token", headers=KEY, json={"user_id": "u"})
    assert r.status_code == 503


def test_sos_requires_key(client):
    assert client.post("/api/voice/sos", json={"user_id": "u"}).status_code == 401


def test_sos_creates_event(client):
    persistence.reset()
    r = client.post("/api/voice/sos", headers=KEY,
                    json={"user_id": "u-voice", "nature": "stampede", "yatra": "pandharpur"})
    assert r.status_code == 200 and r.json().get("sos_id")
    got = asyncio.run(persistence.list_sos())
    assert any(e["user_id"] == "u-voice" for e in got)
