import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage
from agent.state import new_state
from agent.nodes.intent_router import intent_router, RouteDecision, VALID_INTENTS


def test_route_decision_schema_fields():
    r = RouteDecision(reply="hi", intent="weather")
    assert r.intent == "weather"
    assert "weather" in VALID_INTENTS


def test_sos_flag_forces_drills_sos_without_llm():
    s = new_state("sess", "user")
    s["language"] = "en"
    s["active_yatra"] = "pandharpur"
    s["sos"] = True
    s["messages"] = [HumanMessage(content="help emergency")]
    out = asyncio.run(intent_router(s))
    assert out["intent"] == "drills_sos"
