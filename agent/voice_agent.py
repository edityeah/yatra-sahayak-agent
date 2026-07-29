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
import time
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
from agent.voice.persona import greeting_instruction, instructions_for

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
    message_id:            str | None = None
    user_id:               str | None = None
    conversation_id:       str | None = None
    conversation_title:    str | None = None
    multimodal_session_id: str | None = None
    yatra:                 str | None = None
    language:              str | None = None

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
        # Persona is bound to the caller's SELECTED language so both the voice
        # and the captions open (and stay) in that language.
        self._lang = metadata.language if metadata.language in ("mr", "hi", "en") else "mr"
        super().__init__(instructions=instructions_for(self._lang), tools=ALL_TOOLS, **kwargs)
        self._metadata = metadata

    async def on_enter(self) -> None:
        # Greet the moment the caller connects — in their selected language.
        await self.session.generate_reply(instructions=greeting_instruction(self._lang))


# ---------------------------------------------------------------------------
# End-of-call: push the transcript + summary back so the chat thread can
# show BOTH sides of the voice call, just like a text chat.
# ---------------------------------------------------------------------------

async def _on_shutdown(session: "AgentSession", metadata: JobMetadata, start_time: float) -> None:
    """Pull the transcript off the session, summarise it, and POST both to the
    platform's multimodal-session endpoint. Best-effort — any failure is logged
    and swallowed so call teardown is never disrupted. Heavy imports are lazy
    so idle voice subprocesses stay within Render's memory budget."""
    from agent.voice.agent_api import AgentAPIClient
    from agent.voice.schemas import SessionStatus, SessionUpdatePayload
    from agent.voice.summary import SummaryService

    MAX_TRANSCRIPT_ITEMS = 30
    try:
        duration = int(time.time() - start_time)
        history = session.history.to_dict(exclude_timestamp=False) if session.history else {}
        items = history.get("items") or []
        transcript = [i for i in items if i.get("type") == "message"]
        logger.info("voice call closing — %d transcript items, %ds, session_id=%s",
                    len(transcript), duration, metadata.multimodal_session_id)

        summary = await SummaryService().generate(transcript[-MAX_TRANSCRIPT_ITEMS:], metadata.conversation_title)
        payload = SessionUpdatePayload(
            status=SessionStatus.COMPLETED,
            duration=duration,
            message_id=metadata.message_id or "",
            summary=summary.summary,
            conversation_title=summary.title,
            transcript=transcript,   # full transcript; only the summariser input is capped
        )
        await AgentAPIClient().update_multimodal_session(metadata.multimodal_session_id or "", payload)
    except Exception:
        logger.exception("voice shutdown handler failed — call teardown continues")


# ---------------------------------------------------------------------------
# Worker entry point
# ---------------------------------------------------------------------------

async def entrypoint(ctx: JobContext) -> None:
    start_time = time.time()
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

    # When the call ends, push the transcript + summary back so it appears in
    # the chat thread — the same way a text conversation shows both sides.
    ctx.add_shutdown_callback(lambda: _on_shutdown(session, metadata, start_time))


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
