import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage, AIMessage
from agent.state import new_state
from agent.nodes.intent_router import _keyword_intent
from agent.nodes.activities.darshan import darshan
from agent.nodes.activities.accommodation import accommodation
from agent.nodes.activities.langar import langar
from agent.nodes.activities.amenity import amenity


def _mk(text, yatra="pandharpur", loc=None, awaiting=None):
    s = new_state("c", "u"); s["language"] = "en"; s["active_yatra"] = yatra
    s["messages"] = [HumanMessage(content=text)]
    if loc:
        s["shared_location"] = loc
    if awaiting:
        s["awaiting"] = awaiting
    return s


def _reply(state):
    return state["messages"][-1].content


def test_keyword_routing_for_new_intents():
    assert _keyword_intent("what are the darshan and aarti timings") == "darshan"
    assert _keyword_intent("when is the shahi snan") == "darshan"
    assert _keyword_intent("where can I get free food langar") == "langar"
    assert _keyword_intent("where can I stay tonight, any bhakta niwas") == "accommodation"
    assert _keyword_intent("nearest medical post") == "amenity"
    assert _keyword_intent("nearest drinking water") == "amenity"


def test_darshan_pandharpur_and_kumbh():
    assert "Vitthal" in _reply(asyncio.run(darshan(_mk("darshan", "pandharpur"))))
    kumbh = _reply(asyncio.run(darshan(_mk("snan", "kumbh"))))
    assert "Snan" in kumbh or "snan" in kumbh.lower()
    assert "Ramkund" in kumbh or "Kushavarta" in kumbh


def test_accommodation_lists_tariffs():
    body = _reply(asyncio.run(accommodation(_mk("where to stay"))))
    assert "Bhakta Niwas" in body and "night" in body


def test_responses_end_with_text_followups_no_buttons():
    """Each service closes with a PLAIN-TEXT follow-up suggestion (no [[choices]]
    buttons — they don't render in SwiftChat) cross-linking to related services."""
    for node, needle in ((darshan, "Directions"), (accommodation, "Free food"),
                         (langar, "Nearest medical"), (amenity, "Helpline")):
        body = _reply(asyncio.run(node(_mk("hi"))))
        assert "💬" in body and needle in body
        assert "[[choices" not in body and "·" not in body


def test_langar_nearest_when_location_shared():
    # No location → plain list.
    plain = _reply(asyncio.run(langar(_mk("free food"))))
    assert "langar" in plain.lower() or "annadan" in plain.lower()
    # Near Jejuri → the Jejuri annadan is nearest.
    near = _reply(asyncio.run(langar(_mk("free food", loc={"lat": 18.28, "lng": 74.16}))))
    assert "Nearest" in near and "Jejuri" in near


def test_amenity_sticky_location_flow():
    # Step 1: no location → asks for it and arms the sticky flag with the kind.
    step1 = asyncio.run(amenity(_mk("nearest medical post")))
    assert step1["awaiting"] == "amenity:medical"
    assert "Share your location" in _reply(step1)
    # Step 2: a shared pin (the flag carries the kind) → nearest + flag cleared.
    step2 = asyncio.run(amenity(_mk("(pin)", loc={"lat": 18.28, "lng": 74.16},
                                     awaiting="amenity:medical")))
    assert step2["awaiting"] is None
    assert "Nearest" in _reply(step2)


# ── palkhi tracking + nodal directory, parking (Solapur police data) ──
from agent.nodes.activities.palkhi import palkhi
from agent.nodes.activities.parking import parking
from agent.nodes.activities.signage import signage


def test_palkhi_tracking_and_nodal_directory():
    # Plain tracking query → tracker link + schedule, no full officer dump.
    track = _reply(asyncio.run(palkhi(_mk("where is the palkhi"))))
    assert "ashadhi.solapurpolice.gov.in" in track and "July 2026" in track
    assert "Nodal:" not in track
    # Officer query → statewide directory with tel: links.
    nodal = _reply(asyncio.run(palkhi(_mk("nodal officer contact numbers"))))
    assert "Sant Dnyaneshwar" in nodal and "tel:" in nodal


def test_parking_lists_navigable_lots():
    body = _reply(asyncio.run(parking(_mk("where to park"))))
    assert "maps.app.goo.gl" in body and "Navigate" in body


def test_signage_folds_in_bus_routes():
    body = _reply(asyncio.run(signage(_mk("route map"))))
    assert "bus routes" in body.lower() and "Kolhapur" in body
