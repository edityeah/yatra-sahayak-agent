import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from agent.state import new_state, YATRAS, LANGS


def test_new_state_defaults():
    s = new_state(session_id="sess-1", user_id="user-1")
    assert s["session_id"] == "sess-1"
    assert s["user_id"] == "user-1"
    assert s["policy_result"] == "allowed"
    assert s["language"] is None          # not chosen yet
    assert s["active_yatra"] is None      # not chosen yet
    assert s["intent"] == "browse"
    assert s["sos"] is False
    assert s["messages"] == []


def test_known_yatras_and_langs():
    assert set(YATRAS) == {"pandharpur", "kumbh"}
    assert set(LANGS) == {"mr", "hi", "en"}
