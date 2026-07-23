import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage
from agent.state import new_state
from agent.nodes.activities.helpline import helpline
from agent.nodes.activities.logistics import logistics
from agent.nodes.activities.advisory import advisory
from agent.nodes.activities.signage import signage
from agent.config import get_settings
from agent.seed import load


def _state(lang="en", yatra="pandharpur"):
    s = new_state("sess", "u")
    s["language"] = lang
    s["active_yatra"] = yatra
    s["messages"] = [HumanMessage(content="x")]
    return s


def _reply(node, **kw):
    out = asyncio.run(node(_state(**kw)))
    return out["current_node"], out["messages"][-1].content, out


def test_helpline_has_112_108_and_tel_links():
    node, body, out = _reply(helpline)
    assert node == "helpline"
    assert "112" in body and "108" in body
    assert "tel:112" in body and "tel:108" in body
    # exactly one AIMessage appended
    assert len(out["messages"]) == 2


def test_helpline_lists_every_entry_for_yatra():
    _, body, _ = _reply(helpline, yatra="kumbh")
    entries = load("helplines")["kumbh"]
    for entry in entries:
        assert entry["number"] in body


def test_logistics_has_rate_symbol_and_differs_by_yatra():
    _, p, _ = _reply(logistics, yatra="pandharpur")
    _, k, _ = _reply(logistics, yatra="kumbh")
    assert "₹" in p and "₹" in k and p != k


def test_logistics_includes_all_services_and_notes():
    _, body, _ = _reply(logistics, yatra="pandharpur")
    entries = load("logistics_rates")["pandharpur"]
    for entry in entries:
        assert entry["service"]["en"] in body
        assert entry["rate"] in body
        if "note" in entry:
            assert entry["note"]["en"] in body


def test_advisory_orders_critical_before_info():
    _, body, _ = _reply(advisory)
    if "CRITICAL" in body.upper() and "INFO" in body.upper():
        assert body.upper().index("CRITICAL") < body.upper().rindex("INFO")


def test_advisory_orders_critical_before_warning_before_info():
    entries = load("advisories")["pandharpur"]
    severities = {e["severity"] for e in entries}
    _, body, _ = _reply(advisory)
    upper = body.upper()
    positions = {}
    for sev in ("CRITICAL", "WARNING", "INFO"):
        if sev in severities and sev in upper:
            positions[sev] = upper.index(f"[{sev}]")
    order = list(positions.keys())
    assert order == sorted(order, key=lambda s: {"CRITICAL": 0, "WARNING": 1, "INFO": 2}[s])


def test_advisory_includes_all_titles_and_bodies():
    _, body, _ = _reply(advisory, yatra="kumbh")
    for entry in load("advisories")["kumbh"]:
        assert entry["title"]["en"] in body
        assert entry["body"]["en"] in body


def test_signage_has_map_link():
    _, body, _ = _reply(signage)
    assert f"{get_settings().PUBLIC_WEBVIEW_BASE}/yatri/map?yatra=pandharpur" in body


def test_signage_map_link_reflects_active_yatra():
    _, body, _ = _reply(signage, yatra="kumbh")
    assert f"{get_settings().PUBLIC_WEBVIEW_BASE}/yatri/map?yatra=kumbh" in body


def test_signage_includes_all_locations_and_guidance():
    _, body, _ = _reply(signage, yatra="pandharpur")
    for entry in load("signage")["pandharpur"]:
        assert entry["at"]["en"] in body
        assert entry["guidance"]["en"] in body


def test_marathi_script_used():
    # Marathi output should contain Devanagari for at least one node
    _, body, _ = _reply(helpline, lang="mr")
    assert any("ऀ" <= ch <= "ॿ" for ch in body)


def test_marathi_script_used_across_all_four_nodes():
    for node in (helpline, logistics, advisory, signage):
        _, body, _ = _reply(node, lang="mr")
        assert any("ऀ" <= ch <= "ॿ" for ch in body), f"{node.__name__} missing Devanagari in mr"


def test_all_four_nodes_set_current_node_correctly():
    for node, name in (
        (helpline, "helpline"), (logistics, "logistics"),
        (advisory, "advisory"), (signage, "signage"),
    ):
        out_node, _, _ = _reply(node)
        assert out_node == name
