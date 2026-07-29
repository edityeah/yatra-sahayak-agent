"""AgentAPIClient — POSTs the end-of-call SessionUpdatePayload (transcript +
summary) back to AGENT_API_HOST with an X-API-Key header, so the platform can
render the voice call's transcript into the chat thread after the call.

Best-effort by design: any HTTP failure is logged and swallowed so a flaky
network never disrupts call teardown — the "Voice Call started" chip stands
regardless; we just lose the transcript enrichment.
"""
from __future__ import annotations

import logging

import httpx

from agent.config import get_settings
from agent.voice.schemas import SessionUpdatePayload

logger = logging.getLogger(__name__)


class AgentAPIClient:
    def __init__(self) -> None:
        settings = get_settings()
        self._host = settings.AGENT_API_HOST.rstrip("/")
        self._key = settings.AGENT_API_KEY

    def _configured(self) -> bool:
        return bool(self._host and self._key)

    async def update_multimodal_session(self, session_id: str, payload: SessionUpdatePayload) -> bool:
        if not self._configured():
            logger.info("agent_api not configured (AGENT_API_HOST/AGENT_API_KEY) — skipping transcript upload")
            return False
        if not session_id:
            logger.warning("agent_api upload skipped — no multimodal_session_id in job metadata")
            return False

        url = f"{self._host}/v1/agent/multimodal-session/{session_id}/update"
        body = payload.model_dump(exclude_none=True, mode="json")
        headers = {"X-API-Key": self._key, "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=15.0) as http:
                resp = await http.post(url, json=body, headers=headers)
        except Exception:
            logger.exception("agent_api transcript upload — request failed (session_id=%s)", session_id)
            return False

        if resp.status_code >= 400:
            logger.warning("agent_api transcript upload — %s: %s", resp.status_code, resp.text[:500])
            return False
        logger.info("agent_api transcript upload ok — session_id=%s, %d items",
                    session_id, len(payload.transcript or []))
        return True
