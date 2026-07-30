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
    assert row.get("created_at")                               # raised-at timestamp present
    assert asyncio.run(persistence.set_sos_status(sid, "acknowledged"))


def test_sos_detail_joins_reporter_and_timeline():
    persistence.reset()

    async def run():
        yid = await persistence.create_registration(
            "u-9", yatra="pandharpur", name="Ramesh Patil", phone="9876543210",
            group_name="Patil family", emergency_contact="9820011122",
            medical_flags="Diabetic", age="63", id_type="aadhaar", group_size=4)
        sid = await persistence.create_sos("u-9", yatra="pandharpur", yatra_id=yid,
                                           location="Jejuri", nature="faint")
        await persistence.add_sos_update(sid, status="acknowledged", actor="Insp. Kale",
                                         note="On phone, conscious")
        await persistence.add_sos_update(sid, status="dispatched", actor="Insp. Kale",
                                         note="108 en route", meta={"unit": "108", "eta": "7 min"})
        return await persistence.sos_detail(sid)

    d = asyncio.run(run())
    # who raised it — full registration is joined in
    assert d["reporter"]["name"] == "Ramesh Patil"
    assert d["reporter"]["emergency_contact"] == "9820011122"
    assert d["reporter"]["medical_flags"] == "Diabetic"
    # the incident timeline captured each action with its actor + structured meta
    assert d["status"] == "dispatched"
    assert [u["status"] for u in d["timeline"]] == ["open", "acknowledged", "dispatched"]
    assert d["timeline"][-1]["meta"]["unit"] == "108"
    assert d["timeline"][-1]["actor"] == "Insp. Kale"


def test_sos_update_missing_returns_none():
    persistence.reset()
    assert asyncio.run(persistence.add_sos_update("SOS-NOPE", status="resolved")) is None
    assert asyncio.run(persistence.sos_detail("SOS-NOPE")) is None
