"""signage activity — stub (real route map + turn-by-turn land in Plan 2 Task 8)."""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState


async def signage(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    return {**state, "current_node": "signage",
            "messages": messages + [AIMessage(content="🧭 [signage] Route map + turn-by-turn signage layer. — Plan 2.")]}
