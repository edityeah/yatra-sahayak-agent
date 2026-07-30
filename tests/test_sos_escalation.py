import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from agent import persistence


def test_sos_control_routing_per_yatra():
    assert "Pune" in persistence.sos_control_for("pandharpur")
    assert "Nashik" in persistence.sos_control_for("kumbh")
    assert "112" in persistence.sos_control_for(None)          # default control centre


def test_create_sos_records_escalation_target():
    persistence.reset()
    sid = asyncio.run(persistence.create_sos("u1", yatra="pandharpur", nature="faint", location="Jejuri"))
    rows = asyncio.run(persistence.list_sos())
    row = next(r for r in rows if r["id"] == sid)
    assert row["status"] == "open"                              # = "sent to control room"
    assert "Pune" in (row.get("routed_to") or "")              # escalated to the district control room
    assert asyncio.run(persistence.set_sos_status(sid, "acknowledged"))
