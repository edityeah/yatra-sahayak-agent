"""weather activity — stub (real IMD live+fallback lands in Plan 2 Task 10)."""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState


async def weather(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    return {**state, "current_node": "weather",
            "messages": messages + [AIMessage(content="🌦️ [weather] Route-wise forecast will appear here (IMD, live). — Plan 2.")]}
