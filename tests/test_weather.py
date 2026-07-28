import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from langchain_core.messages import HumanMessage
from agent.state import new_state
from agent import weather_client
from agent.nodes.activities.weather import weather
from agent.nodes.yatra_context import yatra_context


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


def test_weather_node_asks_in_chat_no_webview_no_choices():
    # No origin → ask IN CHAT to share a location or pick a city. No webview
    # link, no simulated [[choices:]] chips. Sets the sticky awaiting flag.
    s = new_state("s", "u"); s["language"] = "en"; s["active_yatra"] = "pandharpur"
    s["messages"] = [HumanMessage(content="what is the weather?")]
    out = asyncio.run(weather(s))
    body = out["messages"][-1].content
    assert out["current_node"] == "weather"
    assert out["awaiting"] == "weather_origin"
    assert "starting from" in body
    assert "Share your location" in body            # native location share
    assert "Mumbai" in body and "Pune" in body       # cities listed as text
    assert "[[choices:" not in body                  # no simulated buttons
    assert "/yatri/weather" not in body              # no webview link
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
    assert out["awaiting"] is None                    # origin satisfied → flag cleared


def test_weather_node_renders_for_location_shared_in_chat(monkeypatch):
    # A location shared natively in chat (lat/lng) → route card, no city needed.
    # The origin is reverse-geocoded so the card NAMES the place (not "Your
    # location"). Mocked so the test doesn't depend on the network geocoder.
    import agent.route_weather as rw
    async def fake_rev(lat, lng): return {"mr": "कोथरूड, पुणे", "hi": "कोथरूड, पुणे", "en": "Kothrud, Pune"}
    monkeypatch.setattr(rw, "reverse_geocode", fake_rev)
    s = new_state("s", "u"); s["language"] = "en"; s["active_yatra"] = "pandharpur"
    s["messages"] = [HumanMessage(content="")]         # location messages carry no text
    s["shared_location"] = {"lat": 18.516, "lng": 73.856}   # Pune
    out = asyncio.run(weather(s))
    body = out["messages"][-1].content
    assert "Weather on your route" in body and "Pandharpur" in body
    assert "Kothrud, Pune" in body                      # names WHERE they are
    assert out["awaiting"] is None


def test_reverse_geocode_never_raises_on_network_failure(monkeypatch):
    # An unreachable geocoder must degrade to the generic label, not error.
    import agent.route_weather as rw
    monkeypatch.setattr(rw, "_NOMINATIM", "http://127.0.0.1:9/nope")
    out = asyncio.run(rw.reverse_geocode(18.516, 73.856))
    assert out["en"] == "Your location"


def test_weather_node_accepts_city_picked_by_number():
    # The ask lists cities 1..6; replying "2" picks Pune.
    s = new_state("s", "u"); s["language"] = "en"; s["active_yatra"] = "pandharpur"
    s["awaiting"] = "weather_origin"
    s["messages"] = [HumanMessage(content="2")]
    out = asyncio.run(weather(s))
    body = out["messages"][-1].content
    assert "Pune" in body and "Weather on your route" in body


def test_origin_city_nashik_does_not_flip_the_yatra():
    # "Nashik" is a starting city AND the Kumbh location. When it's the answer
    # to a weather origin-ask on Pandharpur, it must NOT switch the yatra.
    s = new_state("s", "u"); s["language"] = "en"; s["active_yatra"] = "pandharpur"
    s["awaiting"] = "weather_origin"
    s["messages"] = [HumanMessage(content="Nashik")]
    out = asyncio.run(yatra_context(s))
    assert out["active_yatra"] == "pandharpur"          # not flipped to kumbh
    assert not out.get("just_selected_yatra")           # no yatra-confirm turn
