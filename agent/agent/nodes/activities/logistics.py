"""logistics activity — stub (real notified-rate table lands in Plan 2 Task 6)."""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState


async def logistics(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    return {**state, "current_node": "logistics",
            "messages": messages + [AIMessage(content="🐎 [logistics] Govt-notified pony/transport rates + providers. — Plan 2.")]}
