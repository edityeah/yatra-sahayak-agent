"""Officer war-room agent — answers operational questions over the live DB
(registrations, SOS, lost & found). A separate surface from the yatri bot;
access is allowlist/admin-gated at the webhook. Deterministic DB queries with
an LLM only to classify the ask (fails open to keyword matching).
"""
from __future__ import annotations
import re
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage

from agent.llm import get_main_llm
from agent import persistence

_YATRA = {"pandharpur": "Pandharpur Wari", "kumbh": "Simhastha Kumbh (Nashik)"}


class OfficerIntent(BaseModel):
    intent: str = Field(description="One of: summary sos lostfound find help")
    yatra: str = Field(default="", description="pandharpur | kumbh | '' if not specified")
    query: str = Field(default="", description="search text (a name or Yatra ID) for intent=find")


def _kw_intent(text: str) -> OfficerIntent:
    t = text.lower()
    yatra = "pandharpur" if any(k in t for k in ("pandhar", "wari")) else "kumbh" if any(k in t for k in ("kumbh", "nashik", "nasik")) else ""
    if any(k in t for k in ("sos", "emergency", "missing person", "distress")):
        return OfficerIntent(intent="sos", yatra=yatra)
    if any(k in t for k in ("lost", "found", "belonging", "missing")):
        return OfficerIntent(intent="lostfound", yatra=yatra)
    if any(k in t for k in ("find", "search", "look up", "pwari-", "kumbh-", "yatra id")):
        return OfficerIntent(intent="find", yatra=yatra, query=text)
    if any(k in t for k in ("how many", "count", "headcount", "registered", "summary", "status", "overview", "total")):
        return OfficerIntent(intent="summary", yatra=yatra)
    return OfficerIntent(intent="help", yatra=yatra)


async def _classify(text: str) -> OfficerIntent:
    sys = ("Classify an officer's operational request about a pilgrimage control room.\n"
           "intent: 'summary' (counts/headcount/status), 'sos' (emergencies/SOS feed), "
           "'lostfound' (lost & found reports / missing belongings), 'find' (look up a specific "
           "pilgrim by name or Yatra ID), or 'help'. yatra: pandharpur/kumbh if named. "
           "query: the name or Yatra ID to search for intent=find.")
    try:
        return await get_main_llm().with_structured_output(OfficerIntent).ainvoke(
            [SystemMessage(content=sys), HumanMessage(content=text)])
    except Exception as e:
        print(f"[officer] classify failed, keyword fallback: {e}", flush=True)
        return _kw_intent(text)


async def officer_reply(text: str) -> str:
    intent = await _classify(text)
    yfilter = intent.yatra if intent.yatra in _YATRA else None

    if intent.intent == "summary":
        s = await persistence.officer_summary()
        by = "; ".join(f"{_YATRA.get(k, k)}: {v}" for k, v in s["by_yatra"].items()) or "—"
        return (f"📊 **Control-room summary**\n"
                f"- Pilgrims registered: **{s['pilgrims']}** ({s['families']} family groups)\n"
                f"- By yatra: {by}\n"
                f"- 🆘 Open SOS: **{s['open_sos']}**\n"
                f"- 🧿 Open lost & found: **{s['open_lostfound']}**")

    if intent.intent == "sos":
        sos = [x for x in await persistence.list_sos() if (x.get("status") or "open") == "open"]
        if yfilter:
            sos = [x for x in sos if x.get("yatra") == yfilter]
        if not sos:
            return "🆘 No open SOS events right now."
        lines = [f"🆘 **Open SOS ({len(sos)})**"]
        for x in sos[:15]:
            loc = x.get("location") or "—"
            lines.append(f"- `{x['id']}` — {x.get('nature') or 'SOS'} · 📍 {loc}")
        return "\n".join(lines)

    if intent.intent == "lostfound":
        lf = [x for x in await persistence.list_lost_found(yfilter) if (x.get("status") or "open") == "open"]
        if not lf:
            return "🧿 No open lost & found reports."
        lines = [f"🧿 **Open lost & found ({len(lf)})**"]
        for x in lf[:15]:
            kind = "Person" if x.get("kind") == "person" else "Item"
            lines.append(f"- `{x['id']}` — {kind}: {x.get('name') or '—'} · 📍 {x.get('last_seen') or '—'}")
        return "\n".join(lines)

    if intent.intent == "find":
        q = (intent.query or text).strip().lower()
        q = re.sub(r"\b(find|search|look ?up|pilgrim|yatra id|for)\b", "", q).strip()
        regs = await persistence.list_registrations()
        hits = [r for r in regs if q and (q in (r.get("name", "").lower()) or q in (r.get("yatra_id", "").lower()))]
        if not hits:
            return f"🔎 No pilgrim found matching '{q}'."
        lines = [f"🔎 **{len(hits)} match(es)**"]
        for r in hits[:10]:
            lines.append(f"- **{r.get('name')}** ({r.get('age', '?')}) · `{r.get('yatra_id')}` · "
                         f"{_YATRA.get(r.get('yatra'), r.get('yatra'))} · ☎ {r.get('emergency_contact') or '—'}")
        return "\n".join(lines)

    return ("👮 **Yatra Control** — ask me for a **summary** (headcount), the **SOS** feed, "
            "**lost & found** reports, or to **find** a pilgrim by name or Yatra ID.")
