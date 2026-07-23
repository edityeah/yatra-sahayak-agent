"""drills_sos activity — stub (real drills + live SOS land in Plan 2 Task 9)."""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState


async def drills_sos(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    return {**state, "current_node": "drills_sos",
            "messages": messages + [AIMessage(content="🆘 [drills_sos] Preparedness drills + live SOS to the control room. — Plan 2.")]}
