"""LangGraph build — the Yatra Sahayak spine.

  content_policy ── blocked ─────────────────► END (canned refusal)
        │ allowed
        ▼
  language_gate ── language is None ─────────► END (selection prompt)
        │ language set
        ▼
  yatra_context ── active_yatra is None ─────► END (yatra-ask prompt)
        │ yatra set
        ▼
  intent_router
        │ intent
        ├── weather | advisory | logistics | helpline
        │   | drills_sos | signage | registration ─► activity node ─► END
        └── browse | answer | off_topic ───────────► END (router already replied)
"""
from __future__ import annotations
from langgraph.graph import StateGraph, END

from agent.state import YatraState
from agent.nodes.content_policy import content_policy
from agent.nodes.language_gate import language_gate
from agent.nodes.yatra_context import yatra_context
from agent.nodes.intent_router import intent_router
from agent.nodes.activities import ACTIVITY_NODES

_ACTIVITY_INTENTS = ("weather", "advisory", "logistics", "helpline", "drills_sos", "signage", "registration", "lost_found", "grievance", "darshan", "accommodation", "langar", "amenity")


def _after_policy(state: YatraState):
    if state.get("policy_result") == "blocked":
        return END
    if state.get("sos"):
        return "intent_router"   # emergency: skip language/yatra gates
    return "language_gate"


def _after_language(state: YatraState):
    return END if state.get("language") is None else "yatra_context"


def _after_yatra(state: YatraState):
    if state.get("active_yatra") is None:
        return END
    if state.get("just_selected_yatra"):   # bare pick → confirmation already sent
        return END
    return "intent_router"


def _after_router(state: YatraState):
    intent = state.get("intent")
    if intent in _ACTIVITY_INTENTS:
        return intent
    return END  # browse | answer | off_topic — reply already on state


def build_graph():
    g = StateGraph(YatraState)
    g.add_node("content_policy", content_policy)
    g.add_node("language_gate", language_gate)
    g.add_node("yatra_context", yatra_context)
    g.add_node("intent_router", intent_router)
    for name, node in ACTIVITY_NODES.items():
        g.add_node(name, node)

    g.set_entry_point("content_policy")
    g.add_conditional_edges("content_policy", _after_policy)
    g.add_conditional_edges("language_gate", _after_language)
    g.add_conditional_edges("yatra_context", _after_yatra)
    g.add_conditional_edges("intent_router", _after_router)
    for name in ACTIVITY_NODES:
        g.add_edge(name, END)

    return g.compile()


# Compiled once at import — thread-safe, shared across requests.
yatra_graph = build_graph()
