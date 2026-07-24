import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage
from agent.state import new_state
from agent import persistence
from agent.nodes.activities.registration import registration
from agent.nodes.intent_router import intent_router
from agent.nodes.content_policy import content_policy
from agent.nodes.yatra_context import yatra_context


def _turn(state, text):
    state = dict(state)
    state["messages"] = (state.get("messages") or []) + [HumanMessage(content=text)]
    return asyncio.run(registration(state))


def test_solo_intake_issues_one_pass():
    persistence.reset()
    s = new_state("sess", "u-reg"); s["language"] = "en"
    # yatra → name → age → phone → otp → ekyc → group → emergency → medical → add_member → confirm
    s = _turn(s, "register me"); assert s["reg_stage"] == "yatra"
    s = _turn(s, "1"); assert s["reg_stage"] == "name" and s["active_yatra"] == "pandharpur"
    s = _turn(s, "Asha Patil"); assert s["reg_stage"] == "age"
    s = _turn(s, "45"); assert s["reg_stage"] == "phone"
    s = _turn(s, "9812345678"); assert s["reg_stage"] == "otp"
    s = _turn(s, "123456"); assert s["reg_stage"] == "ekyc"
    s = _turn(s, "Aadhaar"); assert s["reg_stage"] == "group"
    s = _turn(s, "Alandi Dindi"); assert s["reg_stage"] == "emergency"
    s = _turn(s, "Sunil 9800000000"); assert s["reg_stage"] == "medical"
    s = _turn(s, "diabetes"); assert s["reg_stage"] == "add_member"
    s = _turn(s, "done"); assert s["reg_stage"] == "confirm"
    assert "Asha Patil" in s["messages"][-1].content   # confirm summary
    s = _turn(s, "yes")
    assert s["reg_stage"] == "done"
    body = s["messages"][-1].content
    assert "/yatri/passes?user_id=" in body and "1 pass" in body.lower().replace("(s)", "")
    regs = asyncio.run(persistence.list_registrations_for_user("u-reg"))
    assert len(regs) == 1
    reg = regs[0]
    assert reg["name"] == "Asha Patil" and reg["yatra"] == "pandharpur" and reg["age"] == "45"
    assert reg["group_name"] == "Alandi Dindi" and reg["is_primary"] is True
    assert reg["id_type"] == "Aadhaar" and reg["mobile_verified"] and reg["ekyc_verified"]
    assert "Sunil" in reg["emergency_contact"] and "9800000000" in reg["emergency_contact"]


def test_family_intake_issues_one_pass_per_member():
    persistence.reset()
    s = new_state("sess", "u-fam"); s["language"] = "en"
    s = _turn(s, "register"); s = _turn(s, "1")           # yatra
    s = _turn(s, "Asha Patil"); s = _turn(s, "45")        # primary name, age
    s = _turn(s, "9812345678"); s = _turn(s, "123456")    # phone, otp
    s = _turn(s, "Aadhaar")                                # ekyc
    s = _turn(s, "Alandi Dindi")                           # group
    s = _turn(s, "Sunil 9800000000")                       # emergency
    s = _turn(s, "none")                                   # medical → add_member
    assert s["reg_stage"] == "add_member"
    s = _turn(s, "Ravi Patil"); assert s["reg_stage"] == "member_age"
    s = _turn(s, "12"); assert s["reg_stage"] == "add_member"   # <13 → eligibility flag
    s = _turn(s, "Meena Patil"); s = _turn(s, "40"); assert s["reg_stage"] == "add_member"
    s = _turn(s, "done"); assert s["reg_stage"] == "confirm"
    s = _turn(s, "yes"); assert s["reg_stage"] == "done"
    assert "3 pass" in s["messages"][-1].content.lower().replace("(es)", "")

    regs = asyncio.run(persistence.list_registrations_for_user("u-fam"))
    assert len(regs) == 3
    names = {r["name"] for r in regs}
    assert names == {"Asha Patil", "Ravi Patil", "Meena Patil"}
    # All share one group_id; exactly one primary; members inherit the phone.
    gids = {r["group_id"] for r in regs}
    assert len(gids) == 1 and next(iter(gids))            # single non-empty group_id
    assert sum(1 for r in regs if r["is_primary"]) == 1
    assert all(r["phone"] == "9812345678" for r in regs)  # members inherit primary's mobile
    assert all(r["group_size"] == 3 for r in regs)
    ravi = next(r for r in regs if r["name"] == "Ravi Patil")
    assert "guardian" in ravi["medical_flags"]            # under-13 eligibility flag


def test_ekyc_verifies_by_id_type_and_never_asks_for_aadhaar_number():
    persistence.reset()
    s = new_state("sess", "u2"); s["language"] = "en"
    s = _turn(s, "register"); assert s["reg_stage"] == "yatra"
    s = _turn(s, "2"); s = _turn(s, "Ravi Kumar"); s = _turn(s, "30")
    s = _turn(s, "9812345678"); s = _turn(s, "111111")
    ekyc_prompt = s["messages"][-1].content
    assert s["reg_stage"] == "ekyc"
    # e-KYC offers Aadhaar as an ID *type* but promises never to take/store the
    # number — the privacy guarantee must be present, and it asks for the type.
    assert "never" in ekyc_prompt.lower() and "aadhaar number" in ekyc_prompt.lower()
    s = _turn(s, "Aadhaar")   # answer with just the type — no number needed
    assert s["reg_stage"] == "group" and s["reg_fields"]["ekyc_verified"] is True
    assert s["reg_fields"]["id_type"] == "Aadhaar"


def test_invalid_phone_reprompts_without_advancing():
    persistence.reset()
    s = new_state("sess", "u-bad"); s["language"] = "en"
    s = _turn(s, "register"); s = _turn(s, "1"); s = _turn(s, "Name"); s = _turn(s, "40")
    assert s["reg_stage"] == "phone"
    s = _turn(s, "hello")             # not a valid mobile
    assert s["reg_stage"] == "phone"  # stays put, re-prompts
    s = _turn(s, "9812345678")
    assert s["reg_stage"] == "otp"    # now advances


def test_content_policy_allows_intake_answers_midregistration():
    # Regression: a bare phone number mid-registration must NOT be blocked as
    # off-topic (the LLM classifier is skipped while reg_stage is in progress).
    s = new_state("sess", "u-cp"); s["language"] = "en"; s["reg_stage"] = "phone"
    s["messages"] = [HumanMessage(content="9619334832")]
    out = asyncio.run(content_policy(s))
    assert out["policy_result"] == "allowed"


def test_sticky_router_stays_in_registration():
    s = new_state("sess", "u3"); s["language"] = "en"; s["active_yatra"] = "pandharpur"
    s["reg_stage"] = "phone"; s["messages"] = [HumanMessage(content="9812345678")]
    out = asyncio.run(intent_router(s))
    assert out["intent"] == "registration"   # deterministic, no LLM


def test_reentry_after_done_starts_fresh_without_crash():
    # Regression: re-triggering registration after a prior intake finished
    # ("done") must start a clean intake, not KeyError.
    persistence.reset()
    s = new_state("sess", "u4"); s["language"] = "en"; s["active_yatra"] = "pandharpur"
    s["reg_stage"] = "done"; s["reg_fields"] = {"name": "Old Name"}
    out = _turn(s, "register again")
    assert out["reg_stage"] == "yatra"                    # fresh restart at the first step
    assert out["reg_fields"].get("members") == []         # clean slate
    assert "name" not in out["reg_fields"]                # stale fields cleared
    assert out["messages"][-1].content                    # asked the first question, no crash


def test_yatra_not_switched_during_active_registration():
    # Regression: a Dindi/group answer containing a yatra keyword ("Alandi")
    # must NOT flip the active yatra away from the one being registered.
    s = new_state("sess", "u5"); s["language"] = "en"; s["active_yatra"] = "kumbh"
    s["reg_stage"] = "group"
    s["messages"] = [HumanMessage(content="Alandi Sant Dnyaneshwar Dindi 12")]
    out = asyncio.run(yatra_context(s))
    assert out["active_yatra"] == "kumbh"      # unchanged despite "Alandi"
