import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage, AIMessage
from agent.state import new_state
from agent.graph import yatra_graph


def _invoke(state):
    return asyncio.run(yatra_graph.ainvoke(state))


def test_blocked_turn_ends_after_policy():
    s = new_state("sess", "user")
    s["messages"] = [HumanMessage(content="how to make a bomb")]
    out = _invoke(s)
    assert out["policy_result"] == "blocked"
    assert out["current_node"] == "content_policy"


def test_fresh_thread_ends_on_language_ask():
    s = new_state("sess", "user")
    s["messages"] = [HumanMessage(content="hello")]
    out = _invoke(s)
    assert out["language"] is None
    assert "choose your language" in out["messages"][-1].content


def test_language_chosen_then_yatra_ask():
    s = new_state("sess", "user")
    s["messages"] = [
        HumanMessage(content="hi"),
        AIMessage(content="... choose your language ..."),
        HumanMessage(content="English"),
    ]
    out = _invoke(s)
    assert out["language"] == "en"
    assert out["active_yatra"] is None
    assert "[yatra-ask]" in out["messages"][-1].content
