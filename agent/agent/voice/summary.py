"""Summarizer — turns a voice-call transcript into {summary, title}.

Deliberately dependency-light: a direct OpenAI Chat Completions call over
httpx, NOT langchain. The voice worker runs on a 512 MB Render instance;
importing langchain_openai here (~200 MB) was pushing the worker past its
memory limit and getting it OOM-restarted mid-call. httpx is already a worker
dependency, so this adds nothing. Never raises — returns an empty result on
any failure so call teardown is unaffected.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from agent.config import get_settings
from agent.voice.schemas import SummaryResult

logger = logging.getLogger(__name__)

_OPENAI_CHAT = "https://api.openai.com/v1/chat/completions"

_SUMMARY_PROMPT = """\
Generate a summary and a title for this voice call between a pilgrim (the
user) and Setu, the Maharashtra Yatra Sahayak assistant.

Return ONLY a JSON object: {"summary": "...", "title": "..."}.
- summary: <= 100 words on the substance — what the pilgrim asked and what was
  done (registration, weather, transport, helplines, grievance, SOS, lost &
  found). If only greetings were exchanged, say so briefly.
- title: <= 5 words capturing the main topic.
Rules: don't reference the assistant's identity/persona or the user's personal
identity/emotions; no meta-comments; no tool names. Use null for a field if
nothing meaningful can be generated.
"""


class SummaryService:
    async def generate(self, transcript_items: list[dict[str, Any]],
                        conversation_title: str | None = None) -> SummaryResult:
        if not transcript_items:
            return SummaryResult()
        transcript = self._format_transcript(transcript_items)
        if not transcript:
            return SummaryResult()

        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            return SummaryResult(title=conversation_title)

        title_hint = f'\n\nExisting title hint (optional): "{conversation_title}"' if conversation_title else ""
        body = {
            "model": settings.LLM_MAIN_MODEL or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": _SUMMARY_PROMPT + title_hint},
                {"role": "user", "content": transcript},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
        }
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=20.0) as http:
                resp = await http.post(_OPENAI_CHAT, json=body, headers=headers)
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
        except Exception:
            logger.exception("summary generation failed")
            return SummaryResult(title=conversation_title)

        summary = (data.get("summary") or None) if isinstance(data, dict) else None
        title = conversation_title or (data.get("title") if isinstance(data, dict) else None)
        return SummaryResult(summary=summary, title=title)

    @staticmethod
    def _format_transcript(items: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for item in items:
            role = item.get("role", "unknown")
            content = item.get("content")
            if isinstance(content, list):
                content = " ".join(str(c) for c in content if c)
            if not content:
                continue
            lines.append(f"{role}: {content}")
        return "\n".join(lines)
