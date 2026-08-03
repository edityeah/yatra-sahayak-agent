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


# ── nearest police control routing ──────────────────────────────────
def test_nearest_control_picks_closest_station():
    # A point right at Jejuri (18.277, 74.161) resolves to Jejuri Police Station.
    c = persistence.nearest_control("pandharpur", 18.28, 74.16)
    assert c["name"]["en"] == "Jejuri Police Station"
    assert c["distance_km"] < 2
    # A Kumbh point at Trimbakeshwar resolves to that station, not a Nashik one.
    k = persistence.nearest_control("kumbh", 19.933, 73.530)
    assert k["name"]["en"] == "Trimbakeshwar Police Station"


def test_sos_control_for_uses_coords_else_district():
    with_coords = persistence.sos_control_for("pandharpur", 18.277, 74.161)
    assert "Jejuri Police Station" in with_coords and "112" in with_coords
    # No coordinates → district control room fallback.
    assert persistence.sos_control_for("pandharpur") == "Pune District Control Room · 112 / 1077"


def test_live_location_reroutes_open_sos_to_nearest():
    persistence.reset()

    async def run():
        sid = await persistence.create_sos("u-77", yatra="pandharpur", nature="faint")
        before = await persistence.get_sos(sid)
        updated = await persistence.update_latest_open_sos_location("u-77", 18.277, 74.161)
        return before, updated, await persistence.list_sos_updates(sid)

    before, updated, timeline = asyncio.run(run())
    assert before["lat"] is None                                   # raised without a pin
    assert "Pune District Control Room" in before["routed_to"]     # → district fallback
    assert updated["lat"] == 18.277                                # pin attached
    assert "Jejuri Police Station" in updated["routed_to"]         # → re-routed to nearest
    assert any("re-routed" in (u["note"] or "") for u in timeline)  # logged to the audit trail


def test_danger_phrases_trip_sos():
    from agent.nodes.content_policy import _sos_tripwire
    assert _sos_tripwire("I am in danger")          # the phrase the client named
    assert _sos_tripwire("emergency! help")
    assert _sos_tripwire("मी धोक्यात आहे")           # Marathi: I am in danger
    assert _sos_tripwire("मैं खतरे में हूँ")          # Hindi: I am in danger
    assert not _sos_tripwire("what is the route today")


def test_chat_sos_asks_for_location_then_reroutes():
    """The conversational flow: an SOS with no pin asks for a live location and
    sets the sticky flag; a shared pin then re-routes to the nearest control."""
    persistence.reset()
    from agent.nodes.activities.drills_sos import drills_sos

    async def run():
        # 1) SOS fires with no location.
        s1 = await drills_sos({"sos": True, "user_id": "u-9", "language": "en",
                               "active_yatra": "pandharpur", "messages": []})
        # 2) Pilgrim shares a live pin near Jejuri (router set sos_locate).
        s2 = await drills_sos({"sos_locate": True, "user_id": "u-9", "language": "en",
                               "active_yatra": "pandharpur", "messages": [],
                               "shared_location": {"lat": 18.277, "lng": 74.161}})
        return s1, s2

    s1, s2 = asyncio.run(run())
    ack = s1["messages"][-1].content
    assert "share your live location" in ack.lower()   # asks for the pin
    assert s1["awaiting"] == "sos_location"             # sticky follow-up armed
    confirm = s2["messages"][-1].content
    assert "Jejuri Police Station" in confirm           # re-routed to nearest
    assert s2["awaiting"] is None                        # flag cleared
