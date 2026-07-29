"""LiveKit Voice Agent — Maharashtra Yatra Sahayak (Setu).

Structural mirror of ConveGenius's demo-multimodal-agent-dev pattern.
Uses the OpenAI Realtime API (single voice-to-voice model — no separate
STT / TTS pipeline) with semantic VAD for turn taking.

Dispatch model:
  Our worker registers under `AGENT_NAME` against the project's LiveKit
  instance. The web service's POST /api/voice/token mints a room + token
  and explicitly dispatches a job carrying JobMetadata (user_id / yatra /
  language) to a worker matching `AGENT_NAME`. We accept the job, join
  the room, and stream audio both ways via the Realtime model.

The voice worker has no direct DB access — the raise_sos tool calls back
to the web service's POST /api/voice/sos over HTTP (AGENT_API_HOST /
AGENT_API_KEY). This keeps its dependency surface narrow: OpenAI +
LiveKit + an HTTP client only.

Run with:
    python voice_agent.py start
"""
from __future__ import annotations

import json
import logging
from typing import Any

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RoomInputOptions,
    WorkerOptions,
    cli,
)
from livekit.plugins import openai
from openai.types.beta.realtime.session import TurnDetection, InputAudioTranscription
from pydantic import BaseModel, ValidationError

from agent.config import get_settings
from agent.voice.persona import GREETING, INSTRUCTIONS

# NB: agent.voice.tools is imported LAZILY inside YatraVoiceAssistant.__init__
# so subprocess boot doesn't pay its import cost (httpx, seed data) before
# the worker reports itself available to LiveKit.

settings = get_settings()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Realtime session shape
# ---------------------------------------------------------------------------

REALTIME_MODEL      = "gpt-realtime"
REALTIME_VOICE      = "alloy"
REALTIME_MODALITIES = ["audio"]


# ---------------------------------------------------------------------------
# Job metadata — the web service dispatches with a JSON blob on ctx.job.metadata
# ---------------------------------------------------------------------------

class JobMetadata(BaseModel):
    """Shape the web service sends when dispatching a voice job (see
    POST /api/voice/token in webhook.py). All fields optional so console /
    local dispatches (no metadata) don't crash.
    """
    message_id:      str | None = None
    user_id:         str | None = None
    conversation_id: str | None = None
    yatra:           str | None = None
    language:        str | None = None

    @classmethod
    def parse(cls, raw: str | None) -> "JobMetadata":
        if not raw:
            return cls()
        try:
            return cls.model_validate(json.loads(raw))
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning("job metadata not parseable, ignoring: %s", e)
            return cls()


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class YatraVoiceAssistant(Agent):
    def __init__(self, metadata: JobMetadata, **kwargs: Any) -> None:
        # Lazy import so subprocess boot doesn't pay the tools' import cost.
        from agent.voice.tools import ALL_TOOLS
        super().__init__(instructions=INSTRUCTIONS, tools=ALL_TOOLS, **kwargs)
        self._metadata = metadata

    async def on_enter(self) -> None:
        # Fire the canonical Setu greeting the moment the caller connects —
        # no waiting for them to speak first.
        await self.session.generate_reply(instructions=GREETING)


# ---------------------------------------------------------------------------
# Worker entry point
# ---------------------------------------------------------------------------

async def entrypoint(ctx: JobContext) -> None:
    metadata = JobMetadata.parse(ctx.job.metadata)
    logger.info(
        "voice job received: room=%s user_id=%s yatra=%s language=%s",
        ctx.room.name if ctx.room else None,
        metadata.user_id,
        metadata.yatra,
        metadata.language,
    )

    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            api_key=settings.OPENAI_API_KEY,
            model=REALTIME_MODEL,
            voice=REALTIME_VOICE,
            modalities=REALTIME_MODALITIES,
            # Transcribe the pilgrim's speech too, so the call transcript saved
            # to the chat thread has BOTH sides (not just Setu's replies).
            input_audio_transcription=InputAudioTranscription(model="gpt-4o-mini-transcribe"),
            turn_detection=TurnDetection(
                type="semantic_vad",
                eagerness="auto",
                create_response=True,
                interrupt_response=True,
            ),
        ),
    )

    await session.start(
        room=ctx.room,
        agent=YatraVoiceAssistant(metadata=metadata),
        room_input_options=RoomInputOptions(
            audio_enabled=True,
            video_enabled=False,
        ),
    )


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            ws_url=settings.LIVEKIT_URL,
            api_key=settings.LIVEKIT_API_KEY,
            api_secret=settings.LIVEKIT_API_SECRET,
            agent_name=settings.AGENT_NAME,
            # Render Starter is 512 MB. LiveKit's default of warm idle
            # subprocesses pushes memory past budget; 0 → no warm process,
            # each call pays a short subprocess boot penalty instead.
            num_idle_processes=0,
        )
    )
