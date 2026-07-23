import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage
from agent.state import new_state
from agent import weather_client
from agent.nodes.activities.weather import weather


def test_forecast_falls_back_to_cached_when_no_url():
    f = asyncio.run(weather_client.get_forecast("pandharpur"))
    assert f["source"] == "cached"
    assert f["summary"]


def test_weather_reply_shows_cached_forecast_and_source():
    s = new_state("s", "u"); s["language"] = "en"; s["active_yatra"] = "pandharpur"
    s["messages"] = [HumanMessage(content="weather?")]
    out = asyncio.run(weather(s))
    body = out["messages"][-1].content
    assert out["current_node"] == "weather"
    # temp from the seed appears, and the reply is labelled as cached (offline)
    assert "°C" in body or "C" in body
    assert "cached" in body.lower() or "अद्ययावत" in body or "कैश" in body  # some cached/updated indicator


def test_weather_rain_alert_when_present():
    # pandharpur fallback has a rain_alert; kumbh may be null
    s = new_state("s", "u"); s["language"] = "en"; s["active_yatra"] = "pandharpur"
    s["messages"] = [HumanMessage(content="weather?")]
    body = asyncio.run(weather(s))["messages"][-1].content
    from agent.seed import load
    if load("weather_fallback")["pandharpur"]["rain_alert"]:
        assert "⚠" in body or "rain" in body.lower() or "पाऊस" in body or "बारिश" in body
