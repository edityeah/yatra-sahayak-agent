"""advisory activity — stub (real seed-backed advisories land in Plan 2 Task 7)."""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState


async def advisory(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    return {**state, "current_node": "advisory",
            "messages": messages + [AIMessage(content="📢 [advisory] District advisories & road closures will appear here. — Plan 2.")]}
