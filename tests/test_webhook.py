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
