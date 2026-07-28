import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
import webhook


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "yatra-sahayak-agent"


def test_extract_location_handles_multiple_swiftchat_shapes():
    # We don't hardcode one envelope path — a location can arrive as a content
    # block, an attachment, or a nested object. All must yield (lat, lng).
    pune = (18.516, 73.856)
    shapes = [
        {"content": [{"type": "location", "location": {"latitude": 18.516, "longitude": 73.856}}]},
        {"content": [{"type": "location", "latitude": 18.516, "longitude": 73.856}]},
        {"content": [{"type": "text", "text": {"value": "here"}}],
         "attachments": [{"type": "location", "payload": {"lat": 18.516, "lng": 73.856}}]},
        {"metadata": {"geo": {"lat": 18.516, "lon": 73.856}}},
    ]
    for shp in shapes:
        got = webhook._extract_location(shp)
        assert got is not None
        assert round(got[0], 3) == pune[0] and round(got[1], 3) == pune[1]


def test_extract_location_rejects_non_india_and_text_only():
    # A text-only message has no coordinate.
    assert webhook._extract_location({"content": [{"type": "text", "text": {"value": "hi"}}]}) is None
    # Coordinates outside the India bounding box are ignored (stray numbers).
    assert webhook._extract_location(
        {"content": [{"type": "location", "latitude": 51.5, "longitude": -0.12}]}) is None


def test_messages_requires_api_key(client):
    r = client.post("/messages", json={"user_id": "u", "conversation_id": "c",
                                       "message": {"content": [{"type": "text", "text": {"value": "hi"}}]}})
    assert r.status_code == 401


def test_messages_language_ask_streams(client):
    # A fresh greeting hits only deterministic nodes (no OpenAI call).
    r = client.post(
        "/messages",
        headers={"X-API-Key": "local-dev-key"},
        json={"user_id": "u1", "conversation_id": "c1",
              "message": {"content": [{"type": "text", "text": {"value": "hello"}}]}},
    )
    assert r.status_code == 200
    body = r.text
    assert "choose your language" in body
    assert "event: done" in body


def test_registrations_export_requires_admin_and_returns_rows(client):
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
    from agent import persistence

    persistence.reset()

    # No key → 401.
    assert client.get("/api/registrations").status_code == 401
    # Wrong key → 401.
    assert client.get("/api/registrations", headers={"X-API-Key": "nope"}).status_code == 401

    # Seed two registrations directly in the store.
    import asyncio
    asyncio.run(persistence.create_registration(
        "u1", yatra="pandharpur", name="Asha Patil", phone="9812345678",
        age="45", id_type="Aadhaar", group_name="Alandi Dindi", group_size=4,
        emergency_contact="Sunil 9800000000", medical_flags="diabetes",
        mobile_verified=True, ekyc_verified=True))
    asyncio.run(persistence.create_registration(
        "u2", yatra="kumbh", name="Ravi Kumar", phone="9811111111",
        age="30", id_type="Voter ID", group_name="Solo", group_size=1,
        emergency_contact="Meena 9822222222", medical_flags="none"))

    # Admin key (defaults to the internal key in tests) → JSON with headcount.
    r = client.get("/api/registrations", headers={"X-API-Key": "local-dev-key"})
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2                          # one row per person
    assert data["by_yatra"] == {"pandharpur": 1, "kumbh": 1}
    assert any(row["name"] == "Asha Patil" for row in data["registrations"])

    # CSV export.
    rc = client.get("/api/registrations?format=csv", headers={"X-API-Key": "local-dev-key"})
    assert rc.status_code == 200 and "text/csv" in rc.headers["content-type"]
    assert "yatra_id,yatra,name" in rc.text and "Asha Patil" in rc.text
    persistence.reset()


def test_oneshot_register_endpoint(client):
    # The voice agent registers via POST /api/register (it collects fields by
    # voice, then issues the pass in one shot).
    import sys, os, asyncio
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
    from agent import persistence
    persistence.reset()
    r = client.post("/api/register", headers={"X-API-Key": "local-dev-key"},
                    json={"name": "Voice Caller", "age": "50", "phone": "9812345678",
                          "yatra": "kumbh", "emergency_contact": "Sunil 9800000000"})
    assert r.status_code == 200
    d = r.json()
    assert d["yatra_id"].startswith("KUMBH-") and "/yatri/pass?id=" in d["pass_url"]
    regs = asyncio.run(persistence.list_registrations_for_user("voice-caller"))
    assert regs and regs[0]["name"] == "Voice Caller" and regs[0]["yatra"] == "kumbh"
    persistence.reset()


def test_wallet_lists_all_passes_for_a_user(client):
    import sys, os, asyncio
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
    from agent import persistence
    persistence.reset()
    gid = persistence.new_group_id()
    asyncio.run(persistence.create_registration("uW", yatra="pandharpur", name="A", phone="9812345678",
        group_name="D", emergency_contact="x 9800000000", medical_flags="none", group_id=gid,
        is_primary=True, group_size=2))
    asyncio.run(persistence.create_registration("uW", yatra="pandharpur", name="B", phone="9812345678",
        group_name="D", emergency_contact="x 9800000000", medical_flags="none", group_id=gid,
        is_primary=False, group_size=2))
    assert client.get("/api/passes?user_id=uW").status_code == 401     # key required
    r = client.get("/api/passes?user_id=uW", headers={"X-API-Key": "local-dev-key"})
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2 and {d["name"] for d in data} == {"A", "B"}
    persistence.reset()


def test_rate_limit_returns_429(client, monkeypatch):
    import webhook
    monkeypatch.setattr(webhook.settings, "RATE_LIMIT_PER_MIN", 2)
    webhook._RL.clear()
    def post():
        return client.post("/messages", headers={"X-API-Key": "local-dev-key"},
                           json={"user_id": "rl-user", "conversation_id": "rl",
                                 "message": {"content": [{"type": "text", "text": {"value": "hi"}}]}})
    assert post().status_code == 200
    assert post().status_code == 200
    assert post().status_code == 429          # third within the window is blocked
    webhook._RL.clear()


def test_reply_language_returns_none_for_ambiguous_input():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
    from webhook import _reply_language
    assert _reply_language("hello", "mr") == "en"      # Latin → English
    assert _reply_language("नमस्कार", "hi") == "hi"     # Devanagari → selected
    assert _reply_language("1", "mr") is None           # bare digit → no signal
    assert _reply_language("9619334832", "mr") is None  # phone → no signal
    assert _reply_language("", "en") is None             # empty → no signal


def test_language_sticky_across_ambiguous_turn(client):
    """Regression: typing English (while the webview still sends its Marathi
    default hint) must keep replies in English even when the next answer is a
    bare '1' with no script signal — no mid-flow flip to Marathi."""
    import sys, os, asyncio
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
    from agent import persistence

    conv = "sticky-lang-1"
    asyncio.run(persistence.clear_session(conv)); persistence.reset()

    def post(text):
        return client.post(
            "/messages",
            headers={"X-API-Key": "local-dev-key"},
            json={"user_id": "u-sticky", "conversation_id": conv, "language": "mr",
                  "message": {"content": [{"type": "text", "text": {"value": text}}]}},
        ).text

    try:
        # Turn 1: English text (despite the 'mr' hint) → English yatra ask.
        r1 = post("I want to register")
        assert "Which yatra" in r1 and "कोणत्या" not in r1
        # Turn 2: a bare '1' (no script signal) must STAY English, not flip to mr.
        r2 = post("1")
        assert "कोणत्या" not in r2 and "पूर्ण नाव" not in r2
    finally:
        asyncio.run(persistence.clear_session(conv)); persistence.reset()


def test_multi_turn_persists_language_and_reaches_activity(client):
    """Regression: a real multi-turn conversation must remember the chosen
    language + yatra across turns and reach an activity node — not get stuck
    re-asking. Stays offline (t1/t2 deterministic; t3 fail-open; t4 = SOS)."""
    import sys, os, asyncio
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
    from agent import persistence

    conv = "mt-persist-1"
    asyncio.run(persistence.clear_session(conv))
    persistence.reset()

    def post(text):
        return client.post(
            "/messages",
            headers={"X-API-Key": "local-dev-key"},
            json={"user_id": "u", "conversation_id": conv,
                  "message": {"content": [{"type": "text", "text": {"value": text}}]}},
        ).text

    try:
        # Turn 1: greeting → language ask.
        assert "choose your language" in post("hello")
        # Turn 2: pick Marathi → language accepted, now asks which yatra (NOT the language ask again).
        r2 = post("Marathi")
        assert "choose your language" not in r2
        # Turn 3: pick the yatra → must NOT revert to asking which yatra.
        r3 = post("pandharpur")
        assert "Which yatra" not in r3 and "कोणत्या यात्रे" not in r3
        # Turn 4: emergency → SOS fast-path reaches the real drills_sos activity
        # (creates an SOS event + a calm ack that always mentions 112).
        r4 = post("emergency stampede help")
        assert "112" in r4
    finally:
        asyncio.run(persistence.clear_session(conv))
        persistence.reset()
