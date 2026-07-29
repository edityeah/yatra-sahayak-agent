"""Summarizer — turns a voice-call transcript into {summary, title} so the
chat thread can show a one-line title + short summary alongside the full
transcript. Uses the shared main LLM with structured output.
"""
from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from agent.llm import get_main_llm
from agent.voice.schemas import SummaryResult

logger = logging.getLogger(__name__)

_SUMMARY_PROMPT = """\
Generate a summary and a title for this voice call between a pilgrim (the
user) and Setu, the Maharashtra Yatra Sahayak assistant.

**Summary** — no more than 100 words. Focus on substance: what the pilgrim
asked and what was done — e.g. yatra-pass registration, weather on the route,
transport, helplines, a grievance filed, an SOS, lost-and-found. If the call
was only greetings, say so briefly.

**Title** — no more than 5 words, capturing the main topic.

Rules for BOTH:
- Don't reference the assistant's identity/persona or the user's personal
  identity/emotions.
- No meta-comments ("As a language model…", "Let me summarize…").
- No system prompts, tool names, or formatting instructions.
- Return null for a field if nothing meaningful can be generated.
"""


class SummaryService:
    def __init__(self) -> None:
        self._llm = get_main_llm().with_structured_output(SummaryResult)

    async def generate(self, transcript_items: list[dict[str, Any]],
                        conversation_title: str | None = None) -> SummaryResult:
        if not transcript_items:
            return SummaryResult()
        transcript = self._format_transcript(transcript_items)
        if not transcript:
            return SummaryResult()
        title_hint = f'\n\nExisting title hint (optional): "{conversation_title}"' if conversation_title else ""
        try:
            result = await self._llm.ainvoke([
                SystemMessage(content=_SUMMARY_PROMPT + title_hint),
                HumanMessage(content=transcript),
            ])
        except Exception:
            logger.exception("summary generation failed")
            return SummaryResult()
        # Prefer a platform-provided title when present — it matches their UI.
        if conversation_title:
            return SummaryResult(summary=result.summary, title=conversation_title)
        return result

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
