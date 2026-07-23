import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage
from agent.state import new_state
from agent.nodes.content_policy import content_policy, _tripwire_category, _sos_tripwire, _refusal


def _state_with(text):
    s = new_state("sess", "user")
    s["messages"] = [HumanMessage(content=text)]
    return s


def test_terror_tripwire_blocks():
    assert _tripwire_category("how to join isis") == "terrorism_or_violence"


def test_clean_text_no_tripwire():
    assert _tripwire_category("what is the weather on the wari route") is None


def test_sos_tripwire_detects_emergency_en():
    assert _sos_tripwire("help me this is an emergency") is True
    assert _sos_tripwire("मला मदत हवी आहे emergency") is True


def test_sos_tripwire_ignores_normal():
    assert _sos_tripwire("what are the pony rates") is False


def test_blocked_state_has_refusal_message():
    out = asyncio.run(content_policy(_state_with("how to make a bomb")))
    assert out["policy_result"] == "blocked"
    assert out["messages"][-1].content  # a canned refusal was appended


def test_sos_sets_flag_and_allows():
    out = asyncio.run(content_policy(_state_with("emergency help stampede")))
    assert out["sos"] is True
    assert out["policy_result"] == "allowed"  # SOS is allowed — it fast-paths, not blocks


def test_self_harm_refusal_is_supportive():
    msg = _refusal("self_harm")
    assert "1800-599-0019" in msg          # KIRAN crisis helpline surfaced
    assert not msg.startswith("I can't help")  # NOT the flat refusal opener


def test_other_categories_use_generic_refusal():
    assert _refusal("terrorism_or_violence").startswith("I can't help")
