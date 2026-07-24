import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage
from agent.state import new_state
from agent import persistence
from agent.nodes.activities.lost_found import lost_found


def test_persistence_create_list_resolve():
    persistence.reset()
    lid = asyncio.run(persistence.create_lost_found(
        kind="item", name="Blue jhola", description="cloth bag with a water bottle",
        last_seen="near Wakhari", reporter_name="Asha", reporter_phone="9812345678", yatra="pandharpur"))
    assert lid.startswith("LF-")
    rows = asyncio.run(persistence.list_lost_found("pandharpur"))
    assert len(rows) == 1 and rows[0]["name"] == "Blue jhola" and rows[0]["status"] == "open"
    # other yatra doesn't see it
    assert asyncio.run(persistence.list_lost_found("kumbh")) == []
    assert asyncio.run(persistence.set_lost_found_status(lid, "reunited")) is True
    assert asyncio.run(persistence.list_lost_found())[0]["status"] == "reunited"
    assert asyncio.run(persistence.set_lost_found_status("LF-nope", "reunited")) is False


def test_report_person_also_raises_sos(client):
    persistence.reset()
    r = client.post("/api/lostfound", headers={"X-API-Key": "local-dev-key"},
                    json={"kind": "person", "name": "Ravi (age 8)", "description": "red shirt",
                          "last_seen": "Ramkund", "reporter_phone": "9812345678", "yatra": "kumbh"})
    assert r.status_code == 200 and r.json()["id"].startswith("LF-")
    # a missing person must also create an SOS event (built on SOS)
    sos = asyncio.run(persistence.list_sos())
    assert len(sos) == 1 and "Missing person" in (sos[0]["nature"] or "")
    # it shows on the board, and status can be flipped
    board = client.get("/api/lostfound?yatra=kumbh", headers={"X-API-Key": "local-dev-key"}).json()
    assert len(board) == 1
    lid = board[0]["id"]
    assert client.post(f"/api/lostfound/{lid}/status", headers={"X-API-Key": "local-dev-key"},
                       json={"status": "reunited"}).status_code == 200


def test_lostfound_requires_key(client):
    assert client.get("/api/lostfound").status_code == 401
    assert client.post("/api/lostfound", json={"kind": "item"}).status_code == 401


def test_node_returns_link_and_emergency_number():
    s = new_state("s", "u"); s["language"] = "en"; s["active_yatra"] = "pandharpur"
    s["messages"] = [HumanMessage(content="lost and found")]
    out = asyncio.run(lost_found(s))
    body = out["messages"][-1].content
    assert out["current_node"] == "lost_found"
    assert "/yatri/lostfound?" in body and "112" in body
