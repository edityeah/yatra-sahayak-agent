"""intent_router — classify the turn into one activity intent.

SOS turns (state['sos']=True) skip the LLM and route straight to
drills_sos. Otherwise a structured-output RouteDecision picks one of the
activity intents. For browse/answer/off_topic the router writes the reply
itself; activity intents leave reply="" (the activity node speaks in Plan 2,
a stub speaks in this plan).
"""
from __future__ import annotations
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, AIMessage

from agent.state import YatraState
from agent.llm import get_main_llm
from agent.i18n import LANG_NAME

VALID_INTENTS = {
    "browse", "weather", "advisory", "logistics", "helpline",
    "drills_sos", "signage", "registration", "answer", "off_topic",
}


class RouteDecision(BaseModel):
    reply: str = Field(default="", description="Reply text ONLY for answer/off_topic. Empty for activity intents.")
    intent: str = Field(description="One of: weather advisory logistics helpline drills_sos signage registration answer off_topic browse")


def _system(lang: str, yatra: str) -> str:
    yatra_name = {"pandharpur": "Pandharpur Wari", "kumbh": "Simhastha Kumbh (Nashik)"}[yatra]
    return f"""You route each turn of Maharashtra Yatra Sahayak. The user is on the {yatra_name}. Reply language: {LANG_NAME[lang]} (mirror the user's script).

Pick ONE intent for the latest user turn:
- weather        — weather / rain / heat / forecast on the route or a halt
- advisory       — road closures, diversions, schedule, official advisories
- logistics      — pony / transport / palkhi / porter rates or booking; overcharge complaints
- helpline       — asking for phone numbers / who to call / police / ambulance / control room
- drills_sos     — safety preparedness, drills, first-aid, OR an emergency / SOS
- signage        — directions, route map, which way, signage, turn-by-turn
- registration   — register for the yatra, yatra pass, QR pass, group/Dindi registration
- answer         — a general on-topic question you can answer in 40-80 words
- off_topic      — unrelated to the yatra; politely redirect in {LANG_NAME[lang]}
- browse         — a bare greeting / "what can you do" / "menu"

For weather/advisory/logistics/helpline/drills_sos/signage/registration set reply="" (the app responds).
For answer/off_topic/browse write `reply` in {LANG_NAME[lang]}."""


async def intent_router(state: YatraState) -> YatraState:
    messages = state.get("messages") or []
    lang = state.get("language") or "en"
    yatra = state.get("active_yatra") or "pandharpur"

    # Deterministic SOS fast-path.
    if state.get("sos"):
        return {**state, "current_node": "intent_router", "intent": "drills_sos"}  # type: ignore[typeddict-item]

    try:
        result = await get_main_llm().with_structured_output(RouteDecision).ainvoke([
            SystemMessage(content=_system(lang, yatra)),
            *messages[-6:],
        ])
        intent = result.intent if result.intent in VALID_INTENTS else "answer"
        reply = result.reply or ""
    except Exception as e:
        print(f"[intent_router] LLM failed: {e}", flush=True)
        intent, reply = "answer", ""

    # Activity intents are answered downstream; suppress router reply.
    if intent in {"weather", "advisory", "logistics", "helpline", "drills_sos", "signage", "registration"}:
        reply = ""

    updates: YatraState = {**state, "current_node": "intent_router", "intent": intent}  # type: ignore[typeddict-item]
    if reply:
        updates["messages"] = messages + [AIMessage(content=reply)]
    return updates
