import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage
from agent.state import new_state
from agent import persistence
from agent.nodes.activities.drills_sos import drills_sos


def _run(coro):
    return asyncio.run(coro)


def test_sos_creates_event_and_acks_with_112():
    persistence.reset()
    s = new_state("sess", "u-sos-1"); s["sos"] = True; s["language"] = "en"; s["active_yatra"] = "pandharpur"
    s["messages"] = [HumanMessage(content="stampede help")]
    out = _run(drills_sos(s))
    assert out["current_node"] == "drills_sos"
    assert "112" in out["messages"][-1].content
    events = _run(persistence.list_sos())
    assert any(e["user_id"] == "u-sos-1" for e in events)


def test_sos_without_language_is_trilingual():
    persistence.reset()
    s = new_state("sess", "u-sos-2"); s["sos"] = True  # language None, yatra None
    s["messages"] = [HumanMessage(content="emergency")]
    out = _run(drills_sos(s))
    body = out["messages"][-1].content
    assert "112" in body
    # contains Devanagari (mr/hi lines present) AND some ASCII (en line)
    assert any("ऀ" <= ch <= "ॿ" for ch in body) and any(ch.isascii() and ch.isalpha() for ch in body)
    assert _run(persistence.list_sos())  # event still created


def test_drills_branch_lists_modules():
    persistence.reset()
    s = new_state("sess", "u3"); s["language"] = "en"; s["active_yatra"] = "pandharpur"  # sos falsy
    s["messages"] = [HumanMessage(content="what safety drills should I know")]
    out = _run(drills_sos(s))
    body = out["messages"][-1].content
    assert out["current_node"] == "drills_sos"
    assert body.count("**") >= 4  # at least two bolded module titles
    assert _run(persistence.list_sos()) == []  # drills path creates NO sos event
