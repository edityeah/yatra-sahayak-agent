import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage
from agent.state import new_state
from agent import weather_client
from agent.nodes.activities.weather import weather


def test_wmo_bucket_mapping():
    assert weather_client._bucket(0) == "clear"
    assert weather_client._bucket(3) == "cloudy"
    assert weather_client._bucket(63) == "rain"
    assert weather_client._bucket(95) == "thunder"
    assert weather_client._bucket(None) == "mixed"


def test_cached_fallback_shape():
    f = weather_client._cached("pandharpur")
    assert f["source"] == "cached"
    assert f["summary"] and f.get("temp_c") is not None


def test_bogus_imd_url_falls_back_to_cached(monkeypatch):
    # An unreachable IMD endpoint must degrade to the cached fallback, not error.
    from agent.config import get_settings
    monkeypatch.setattr(get_settings(), "IMD_API_URL", "http://127.0.0.1:9/nope")
    f = asyncio.run(weather_client.get_forecast("pandharpur"))
    assert f["source"] == "cached" and f["summary"]


def test_weather_node_prompts_for_location_when_no_origin():
    # "weather?" with no origin → ask where they're starting from, with chips.
    s = new_state("s", "u"); s["language"] = "en"; s["active_yatra"] = "pandharpur"
    s["messages"] = [HumanMessage(content="what is the weather?")]
    out = asyncio.run(weather(s))
    body = out["messages"][-1].content
    assert out["current_node"] == "weather"
    assert "starting from" in body and "[[choices:" in body
    assert "°C" not in body


def test_weather_node_renders_route_card_for_a_city():
    # A named origin → route weather at the named halts to the destination.
    # Network-agnostic: even if Open-Meteo is unreachable, the halt names +
    # source line render (temps may show as —).
    s = new_state("s", "u"); s["language"] = "en"; s["active_yatra"] = "pandharpur"
    s["messages"] = [HumanMessage(content="weather from Pune")]
    out = asyncio.run(weather(s))
    body = out["messages"][-1].content
    assert "Weather on your route" in body
    assert "Pune" in body and "Pandharpur" in body   # you-are-here + destination
    assert "Source:" in body
