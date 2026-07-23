"""Seed-data loader — reads reference JSON from DATA_DIR, cached per name.
All user-facing strings are trilingual dicts {"mr":.., "hi":.., "en":..}."""
from __future__ import annotations
import json
import os
from functools import lru_cache

from agent.config import get_settings


@lru_cache(maxsize=None)
def load(name: str):
    path = os.path.join(get_settings().DATA_DIR, f"{name}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"seed file not found: {path}")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def t(value, lang: str) -> str:
    """Resolve a trilingual dict (or plain string) to the chosen language."""
    if isinstance(value, dict):
        return value.get(lang) or value.get("en") or next(iter(value.values()), "")
    return str(value)
