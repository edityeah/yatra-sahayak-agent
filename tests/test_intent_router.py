import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage, AIMessage
from agent.state import new_state
from agent.nodes import intent_router as ir
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


# --- LLM-outage resilience: deterministic keyword fallback ---------------------

def test_keyword_intent_maps_safety_critical_turns():
    assert ir._keyword_intent("weather on the route") == "weather"
    assert ir._keyword_intent("i need a helpline number") == "helpline"
    assert ir._keyword_intent("how do i register for the yatra pass") == "registration"
    assert ir._keyword_intent("someone lost their bag") == "lost_found"
    assert ir._keyword_intent("मला हवामान हवे आहे") == "weather"          # Marathi
    assert ir._keyword_intent("मुझे हेल्पलाइन नंबर चाहिए") == "helpline"    # Hindi
    # "route" alone must NOT be stolen by signage (it appears in weather asks)
    assert ir._keyword_intent("what is the weather on the route") == "weather"
    assert ir._keyword_intent("tell me a joke") is None


class _RaisingLLM:
    def with_structured_output(self, *a, **k):
        class _Bound:
            async def ainvoke(self, *a, **k):
                raise RuntimeError("LLM down (401)")
        return _Bound()


def test_router_falls_back_to_keyword_intent_when_llm_down(monkeypatch):
    # LLM unavailable → still route "weather" to the weather activity, not 🙏.
    monkeypatch.setattr(ir, "get_main_llm", lambda: _RaisingLLM())
    s = new_state("c", "u"); s["language"] = "en"; s["active_yatra"] = "pandharpur"
    s["messages"] = [HumanMessage(content="weather on the route")]
    out = asyncio.run(intent_router(s))
    assert out["intent"] == "weather"
    # activity intents leave the reply to the downstream node
    assert not any(isinstance(m, AIMessage) for m in out["messages"])


def test_router_never_emits_empty_reply_when_llm_down(monkeypatch):
    # A generic turn with the LLM down must still get a helpful menu, never empty.
    monkeypatch.setattr(ir, "get_main_llm", lambda: _RaisingLLM())
    s = new_state("c", "u"); s["language"] = "en"; s["active_yatra"] = "pandharpur"
    s["messages"] = [HumanMessage(content="tell me a joke")]
    out = asyncio.run(intent_router(s))
    assert out["intent"] == "answer"
    replies = [str(m.content) for m in out["messages"] if isinstance(m, AIMessage)]
    assert replies and replies[-1].strip()          # non-empty
    assert "weather" in replies[-1].lower()


def test_router_routes_shared_location_to_weather(monkeypatch):
    # A location shared in chat with NO text and no pending ask still routes to
    # weather (a shared pin is only meaningful to route weather today).
    monkeypatch.setattr(ir, "get_main_llm", lambda: _RaisingLLM())
    s = new_state("c", "u"); s["language"] = "en"; s["active_yatra"] = "pandharpur"
    s["shared_location"] = {"lat": 19.076, "lng": 72.877}
    s["messages"] = [HumanMessage(content="")]
    out = asyncio.run(intent_router(s))
    assert out["intent"] == "weather"


def test_router_keyword_fallback_menu_is_trilingual(monkeypatch):
    monkeypatch.setattr(ir, "get_main_llm", lambda: _RaisingLLM())
    for lang in ("mr", "hi", "en"):
        s = new_state("c", "u"); s["language"] = lang; s["active_yatra"] = "pandharpur"
        s["messages"] = [HumanMessage(content="xyzzy nonsense")]
        out = asyncio.run(intent_router(s))
        reply = [str(m.content) for m in out["messages"] if isinstance(m, AIMessage)][-1]
        assert reply.strip()   # each language has a non-empty menu
