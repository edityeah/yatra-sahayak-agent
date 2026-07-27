import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
import pytest
from agent import persistence
import agent.officer as officer


@pytest.fixture(autouse=True)
def _kw_only(monkeypatch):
    # Hermetic: skip the LLM classifier, use the keyword fallback directly.
    async def c(text):
        return officer._kw_intent(text)
    monkeypatch.setattr(officer, "_classify", c)


def _seed():
    persistence.reset()
    asyncio.run(persistence.create_registration("u1", yatra="pandharpur", name="Asha Patil", phone="9812345678",
        group_name="Alandi Dindi", group_size=2, emergency_contact="Sunil 9800000000", medical_flags="none",
        age="45", id_type="Aadhaar", group_id="GRP-1", is_primary=True))
    asyncio.run(persistence.create_registration("u1", yatra="pandharpur", name="Ravi Patil", phone="9812345678",
        group_name="Alandi Dindi", group_size=2, emergency_contact="Sunil 9800000000", medical_flags="none",
        age="12", group_id="GRP-1", is_primary=False))
    asyncio.run(persistence.create_sos("u9", yatra="pandharpur", nature="stampede", location="Wakhari"))


def test_officer_summary_reply():
    _seed()
    out = asyncio.run(officer.officer_reply("give me a headcount summary"))
    assert "Pilgrims registered" in out and "2" in out and "Open SOS" in out


def test_officer_sos_reply():
    _seed()
    out = asyncio.run(officer.officer_reply("show me open SOS"))
    assert "Open SOS" in out and "stampede" in out


def test_officer_find_reply():
    _seed()
    out = asyncio.run(officer.officer_reply("find pilgrim Asha"))
    assert "Asha Patil" in out and "PWARI" in out


def test_officer_summary_endpoint(client):
    _seed()
    assert client.get("/api/officer/summary").status_code == 401           # needs admin key
    r = client.get("/api/officer/summary", headers={"X-API-Key": "local-dev-key"})
    assert r.status_code == 200 and r.json()["pilgrims"] == 2 and r.json()["open_sos"] == 1


def test_sos_feed_and_resolve(client):
    _seed()
    feed = client.get("/api/sos?status=open", headers={"X-API-Key": "local-dev-key"}).json()
    assert len(feed) == 1
    sid = feed[0]["id"]
    assert client.post(f"/api/sos/{sid}/status", headers={"X-API-Key": "local-dev-key"},
                       json={"status": "resolved"}).status_code == 200
    assert client.get("/api/sos?status=open", headers={"X-API-Key": "local-dev-key"}).json() == []


def test_officer_chat_gated(client):
    _seed()
    body = {"user_id": "someone", "message": {"content": [{"type": "text", "text": {"value": "summary"}}]}}
    assert client.post("/officer/messages", json=body).status_code == 403          # no key, not allowlisted
    r = client.post("/officer/messages", headers={"X-Admin-Key": "local-dev-key"}, json=body)
    assert r.status_code == 200 and "Pilgrims registered" in r.text


def test_officer_bot_needs_valid_signature(client, monkeypatch):
    # With a webhook secret + allowlist, an allowlisted user_id ALONE is not
    # enough — the request must carry a valid HMAC signature (anti-spoof).
    import hmac, hashlib, json as _json, webhook
    monkeypatch.setattr(webhook.settings, "SWIFTCHAT_WEBHOOK_SECRET", "s3cret")
    monkeypatch.setattr(webhook.settings, "OFFICER_IDS", frozenset({"officer-1"}))
    webhook._RL.clear()
    body = {"user_id": "officer-1", "message": {"content": [{"type": "text", "text": {"value": "summary"}}]}}
    raw = _json.dumps(body).encode()
    # allowlisted user, but no signature → 403
    assert client.post("/officer/messages", content=raw,
                       headers={"Content-Type": "application/json"}).status_code == 403
    # valid signature → 200
    sig = hmac.new(b"s3cret", raw, hashlib.sha256).hexdigest()
    r = client.post("/officer/messages", content=raw,
                    headers={"Content-Type": "application/json", "X-Signature": sig})
    assert r.status_code == 200 and "Pilgrims registered" in r.text
    webhook._RL.clear()
