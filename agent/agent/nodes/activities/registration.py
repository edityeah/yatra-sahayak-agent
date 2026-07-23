"""registration activity — stub (real simulated-eKYC intake + QR pass lands in Plan 2 Task 11)."""
from __future__ import annotations
from langchain_core.messages import AIMessage
from agent.state import YatraState


async def registration(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    return {**state, "current_node": "registration",
            "messages": messages + [AIMessage(content="🪪 [registration] Simulated e-KYC → QR yatra pass. — Plan 2.")]}
