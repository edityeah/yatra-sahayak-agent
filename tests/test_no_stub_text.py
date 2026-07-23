"""Integration guard: no activity node may still return Plan-1 stub text.

Each of the seven activities is exercised with a prepared state (language +
yatra set) and asserted to produce real content, not the '— Plan 2.'
placeholder that the stubs emitted.
"""
import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage
from agent.state import new_state
from agent import persistence
from agent.nodes.activities import ACTIVITY_NODES


def _state(sos=False):
    s = new_state("sess", "u-nostub")
    s["language"] = "en"
    s["active_yatra"] = "pandharpur"
    s["sos"] = sos
    s["messages"] = [HumanMessage(content="hello")]
    return s


def test_no_activity_returns_stub_text():
    persistence.reset()
    for name, node in ACTIVITY_NODES.items():
        state = _state(sos=(name == "drills_sos"))  # exercise the SOS branch too
        out = asyncio.run(node(state))
        body = out["messages"][-1].content
        assert "— Plan 2." not in body, f"{name} still returns stub text"
        assert body.strip(), f"{name} returned empty"


def test_english_logistics_has_no_stray_devanagari_rate():
    # Regression: the 'Free' rate must not leak Marathi into an English render.
    persistence.reset()
    from agent.nodes.activities.logistics import logistics
    s = _state()
    s["active_yatra"] = "kumbh"
    out = asyncio.run(logistics(s))
    assert "मोफत" not in out["messages"][-1].content
