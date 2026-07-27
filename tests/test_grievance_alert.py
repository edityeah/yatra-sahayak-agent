import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage
from agent.state import new_state
from agent import persistence
from agent.nodes.activities.grievance import grievance


def test_grievance_create_list_resolve(client):
    persistence.reset()
    r = client.post("/api/grievances", headers={"X-API-Key": "local-dev-key"},
                    json={"category": "overcharging", "description": "pony charged 3x the rate",
                          "location": "Wakhari", "reporter_phone": "9812345678", "yatra": "pandharpur"})
    assert r.status_code == 200 and r.json()["id"].startswith("GRV-")
    board = client.get("/api/grievances?yatra=pandharpur", headers={"X-API-Key": "local-dev-key"}).json()
    assert len(board) == 1 and board[0]["category"] == "overcharging"
    gid = board[0]["id"]
    assert client.post(f"/api/grievances/{gid}/status", headers={"X-API-Key": "local-dev-key"},
                       json={"status": "resolved"}).status_code == 200
    persistence.reset()


def test_grievance_requires_key(client):
    assert client.get("/api/grievances").status_code == 401


def test_grievance_node_links_to_form():
    s = new_state("s", "u"); s["language"] = "en"; s["active_yatra"] = "pandharpur"
    s["messages"] = [HumanMessage(content="I want to file a complaint")]
    out = asyncio.run(grievance(s))
    body = out["messages"][-1].content
    assert out["current_node"] == "grievance" and "/yatri/grievance?" in body


def test_alerts_create_and_public_read(client):
    persistence.reset()
    r = client.post("/api/alerts", headers={"X-API-Key": "local-dev-key"},
                    json={"title": "Heavy rain", "message": "Avoid the ghat at Wakhari",
                          "severity": "warning", "yatra": "pandharpur"})
    assert r.status_code == 200 and r.json()["id"].startswith("ALRT-")
    # pilgrims read active alerts (either key)
    pub = client.get("/api/alerts?yatra=pandharpur", headers={"X-API-Key": "local-dev-key"}).json()
    assert len(pub) == 1 and pub[0]["title"] == "Heavy rain"
    # kumbh pilgrims don't see a pandharpur-scoped alert
    assert client.get("/api/alerts?yatra=kumbh", headers={"X-API-Key": "local-dev-key"}).json() == []
    aid = pub[0]["id"]
    assert client.post(f"/api/alerts/{aid}/deactivate", headers={"X-API-Key": "local-dev-key"}).status_code == 200
    assert client.get("/api/alerts?yatra=pandharpur", headers={"X-API-Key": "local-dev-key"}).json() == []
    persistence.reset()


def test_officer_summary_includes_grievances(client):
    persistence.reset()
    asyncio.run(persistence.create_grievance(category="facilities", description="no water",
                location="Lonand", reporter_name="", reporter_phone="", yatra="pandharpur"))
    s = client.get("/api/officer/summary", headers={"X-API-Key": "local-dev-key"}).json()
    assert s["open_grievances"] == 1
    persistence.reset()
