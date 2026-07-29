import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from agent.voice import tools
from agent import seed


def _tool_names():
    return {t.info.name for t in tools.ALL_TOOLS}


def test_voice_covers_every_text_activity():
    # Each chat activity must have a matching voice tool so a caller can do
    # everything a chat user can.
    names = _tool_names()
    coverage = {
        "weather": "get_weather",
        "advisory": "get_advisories",
        "logistics": "get_transport_rates",
        "helpline": "get_helplines",
        "drills_sos": "raise_sos",
        "signage": "get_route_info",
        "registration": "register_for_yatra",
        "lost_found": "report_lost_found",
        "grievance": "file_grievance",
    }
    missing = {act: tool for act, tool in coverage.items() if tool not in names}
    assert not missing, f"voice tools missing coverage: {missing}"


def test_read_tools_have_seed_data_for_both_yatras():
    # The DB-free read tools depend on seed data — it must exist for both yatras.
    for name in ("advisories", "logistics_rates", "routes", "itinerary", "helplines"):
        data = seed.load(name)
        for yatra in ("pandharpur", "kumbh"):
            assert data.get(yatra), f"{name}.json has no data for {yatra}"
