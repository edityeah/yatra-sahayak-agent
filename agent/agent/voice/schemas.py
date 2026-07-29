"""Voice-session schemas — the payload shape SwiftChat / ConveGenius expects
for the end-of-call transcript + summary upload. One file so the sender
(voice_agent.py) and any receiver validate against the exact same contract.
Mirrors the swift-learning-agent (Pravasi Setu) contract the team already uses.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    COMPLETED = "completed"
    FAILED    = "failed"


class SummaryResult(BaseModel):
    """Structured output from the summarizer LLM."""
    summary: str | None = None
    title:   str | None = None


class SessionUpdatePayload(BaseModel):
    """Body for POST /v1/agent/multimodal-session/{session_id}/update.

    The platform consumes this to render the voice call's transcript (and a
    summary) into the chat thread after the call ends — the same way a text
    chat shows both sides.
    """
    status:              SessionStatus
    duration:            int             = Field(..., ge=0, description="Total call duration in seconds")
    message_id:          str
    summary:             str | None      = None
    conversation_title:  str | None      = None
    transcript:          list[dict[str, Any]] | None = None
