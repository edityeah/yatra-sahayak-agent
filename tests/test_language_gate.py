import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage, AIMessage
from agent.state import new_state
from agent.i18n import detect_language_choice, LANG_ASK_MARKER
from agent.nodes.language_gate import language_gate, _current_language


def test_detect_language_choice():
    assert detect_language_choice("Marathi") == "mr"
    assert detect_language_choice("मराठी") == "mr"
    assert detect_language_choice("hindi") == "hi"
    assert detect_language_choice("English") == "en"
    assert detect_language_choice("blah") is None


def test_fresh_thread_asks_language():
    s = new_state("sess", "user")
    s["messages"] = [HumanMessage(content="नमस्कार")]
    out = asyncio.run(language_gate(s))
    assert out["language"] is None
    assert LANG_ASK_MARKER in out["messages"][-1].content


def test_language_pick_is_recorded():
    s = new_state("sess", "user")
    s["messages"] = [
        HumanMessage(content="hi"),
        AIMessage(content="... choose your language ..."),
        HumanMessage(content="Marathi"),
    ]
    out = asyncio.run(language_gate(s))
    assert out["language"] == "mr"


def test_current_language_from_history():
    msgs = [
        HumanMessage(content="hi"),
        AIMessage(content="[lang:hi] नमस्ते"),
    ]
    assert _current_language(msgs) == "hi"
