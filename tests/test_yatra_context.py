import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage, AIMessage
from agent.state import new_state
from agent.nodes.yatra_context import yatra_context, detect_yatra, _current_yatra


def test_detect_yatra():
    assert detect_yatra("I'm walking the Pandharpur Wari") == "pandharpur"
    assert detect_yatra("पंढरपूर वारी") == "pandharpur"
    assert detect_yatra("going to the Nashik Kumbh") == "kumbh"
    assert detect_yatra("सिंहस्थ कुंभ") == "kumbh"
    assert detect_yatra("what is the weather") is None


def test_asks_yatra_when_none_chosen():
    s = new_state("sess", "user")
    s["language"] = "en"
    s["messages"] = [HumanMessage(content="what's the weather")]
    out = asyncio.run(yatra_context(s))
    assert out["active_yatra"] is None
    assert "[yatra-ask]" in out["messages"][-1].content


def test_switch_yatra_mid_thread():
    s = new_state("sess", "user")
    s["language"] = "en"
    s["messages"] = [
        HumanMessage(content="pandharpur"),
        AIMessage(content="[yatra:pandharpur] ..."),
        HumanMessage(content="switch to the kumbh"),
    ]
    out = asyncio.run(yatra_context(s))
    assert out["active_yatra"] == "kumbh"


def test_current_yatra_from_history():
    msgs = [AIMessage(content="[yatra:pandharpur] hi")]
    assert _current_yatra(msgs) == "pandharpur"
