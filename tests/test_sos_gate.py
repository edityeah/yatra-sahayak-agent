import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage
from agent.state import new_state
from agent.graph import yatra_graph


def test_first_turn_sos_reaches_drills_sos():
    s = new_state("sess", "user")
    s["messages"] = [HumanMessage(content="emergency stampede help")]
    out = asyncio.run(yatra_graph.ainvoke(s))
    assert out["current_node"] == "drills_sos"
    assert "choose your language" not in out["messages"][-1].content
