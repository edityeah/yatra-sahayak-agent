import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage
from agent.state import new_state
from agent.nodes.activities import ACTIVITY_NODES


def _run(node):
    s = new_state("sess", "user")
    s["language"] = "en"
    s["active_yatra"] = "pandharpur"
    s["messages"] = [HumanMessage(content="test")]
    return asyncio.run(node(s))


def test_all_activity_nodes_exist():
    assert set(ACTIVITY_NODES) == {
        "weather", "advisory", "logistics", "helpline",
        "drills_sos", "signage", "registration", "lost_found", "grievance",
    }


def test_each_stub_appends_a_reply():
    for name, node in ACTIVITY_NODES.items():
        out = _run(node)
        assert out["current_node"] == name
        assert out["messages"][-1].content  # non-empty placeholder reply
