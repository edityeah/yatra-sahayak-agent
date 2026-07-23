def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "yatra-sahayak-agent"


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


def test_multi_turn_persists_language_and_reaches_activity(client):
    """Regression: a real multi-turn conversation must remember the chosen
    language + yatra across turns and reach an activity node — not get stuck
    re-asking. Stays offline (t1/t2 deterministic; t3 fail-open; t4 = SOS)."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
    from agent import session_store

    conv = "mt-persist-1"
    session_store.clear(conv)

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
        # Turn 4: emergency → SOS fast-path reaches the drills_sos activity stub.
        r4 = post("emergency stampede help")
        assert "drills_sos" in r4
    finally:
        session_store.clear(conv)
