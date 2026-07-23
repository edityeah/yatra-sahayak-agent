import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage
from agent.state import new_state
from agent import persistence
from agent.nodes.activities.registration import registration
from agent.nodes.intent_router import intent_router
from agent.nodes.yatra_context import yatra_context


def _turn(state, text):
    state = dict(state)
    state["messages"] = (state.get("messages") or []) + [HumanMessage(content=text)]
    return asyncio.run(registration(state))


def test_full_intake_issues_yatra_id_and_row():
    persistence.reset()
    s = new_state("sess", "u-reg"); s["language"] = "en"; s["active_yatra"] = "pandharpur"
    # start
    s2 = _turn(s, "register me"); assert s2["reg_stage"] == "name"
    s3 = _turn(s2, "Asha Patil"); assert s3["reg_stage"] == "phone"
    s4 = _turn(s3, "+919812345678"); assert s4["reg_stage"] == "group"
    s5 = _turn(s4, "Dindi 5"); assert s5["reg_stage"] == "emergency"
    s6 = _turn(s5, "+919800000000"); assert s6["reg_stage"] == "medical"
    s7 = _turn(s6, "elderly"); assert s7["reg_stage"] == "confirm"
    assert "Asha Patil" in s7["messages"][-1].content   # confirm summary
    s8 = _turn(s7, "yes")
    assert s8["reg_stage"] == "done"
    body = s8["messages"][-1].content
    assert "Yatra ID" in body and "/yatri/pass?id=" in body
    reg = asyncio.run(persistence.get_registration_for_user("u-reg"))
    assert reg and reg["name"] == "Asha Patil" and reg["group_name"] == "Dindi 5"


def test_ekyc_never_asks_for_aadhaar_number():
    persistence.reset()
    s = new_state("sess", "u2"); s["language"] = "en"; s["active_yatra"] = "kumbh"
    out = _turn(s, "register")
    body_lower = out["messages"][-1].content.lower()
    # Simulated e-KYC must reassure that no real Aadhaar number is needed,
    # and the phrase "aadhaar number" must appear only in that reassurance —
    # never as an actual request for one.
    assert "no aadhaar number needed" in body_lower
    assert body_lower.count("aadhaar number") == 1
    assert "enter your aadhaar" not in body_lower and "your aadhaar number" not in body_lower


def test_sticky_router_stays_in_registration():
    s = new_state("sess", "u3"); s["language"] = "en"; s["active_yatra"] = "pandharpur"
    s["reg_stage"] = "phone"; s["messages"] = [HumanMessage(content="+919812345678")]
    out = asyncio.run(intent_router(s))
    assert out["intent"] == "registration"   # deterministic, no LLM


def test_reentry_after_done_starts_fresh_without_crash():
    # Regression: re-triggering registration after a prior intake finished
    # ("done") must start a clean intake, not KeyError on _PROMPTS[None].
    persistence.reset()
    s = new_state("sess", "u4"); s["language"] = "en"; s["active_yatra"] = "pandharpur"
    s["reg_stage"] = "done"; s["reg_fields"] = {"name": "Old Name"}
    out = _turn(s, "register again")
    assert out["reg_stage"] == "name"          # fresh restart
    assert out["reg_fields"] == {}             # stale fields cleared
    assert out["messages"][-1].content          # asked for the name, no crash


def test_yatra_not_switched_during_active_registration():
    # Regression: a Dindi/group answer containing a yatra keyword ("Alandi")
    # must NOT flip the active yatra away from the one being registered.
    s = new_state("sess", "u5"); s["language"] = "en"; s["active_yatra"] = "kumbh"
    s["reg_stage"] = "group"
    s["messages"] = [HumanMessage(content="Alandi Sant Dnyaneshwar Dindi 12")]
    out = asyncio.run(yatra_context(s))
    assert out["active_yatra"] == "kumbh"      # unchanged despite "Alandi"
