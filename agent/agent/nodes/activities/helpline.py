"""helpline activity — stub (real 112/108/control-room dialling lands in Plan 2 Task 5)."""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState


async def helpline(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    return {**state, "current_node": "helpline",
            "messages": messages + [AIMessage(content="☎️ [helpline] One-tap 112 / 108 / control-room dialling. — Plan 2.")]}
