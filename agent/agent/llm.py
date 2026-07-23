"""Shared LLM factory — the single place that constructs the main ChatOpenAI
client, so the api-key fallback and settings read aren't duplicated per node."""
from __future__ import annotations
from functools import lru_cache
from langchain_openai import ChatOpenAI

from agent.config import get_settings


@lru_cache(maxsize=1)
def get_main_llm() -> ChatOpenAI:
    s = get_settings()
    return ChatOpenAI(
        model=s.LLM_MAIN_MODEL,
        temperature=0,
        # Placeholder lets the client construct at import time when no key is
        # configured (the newer OpenAI SDK raises at construction otherwise).
        # Never reached on the deterministic node paths; overridden by a real
        # OPENAI_API_KEY in prod.
        api_key=s.OPENAI_API_KEY or "sk-local-placeholder",
    )
