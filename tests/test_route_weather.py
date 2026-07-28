import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from agent import route_weather as rw


def test_route_stops_ordered_to_destination():
    stops = rw.route_stops("pandharpur")
    assert len(stops) >= 2
    assert stops[-1]["name"]["en"] == "Pandharpur"          # destination last
    # earlier stops are farther from the destination than later ones
    d = rw._DEST["pandharpur"]
    assert rw._hav(stops[0], d) > rw._hav(stops[-2], d)


def test_resolve_city():
    assert rw.resolve_city("weather from Pune")["name"]["en"] == "Pune"
    assert rw.resolve_city("i'm in aurangabad")["name"]["en"] == "Chh. Sambhajinagar"  # alias
    assert rw.resolve_city("somewhere random") is None


def test_route_weather_shape():
    # Network-agnostic: origin is first (you=True), destination last; each point
    # has the expected keys (temps may be None if Open-Meteo is unreachable).
    pts = asyncio.run(rw.route_weather(18.516, 73.856, "pandharpur", {"en": "Pune"}))
    assert len(pts) >= 2 and pts[0]["you"] is True
    assert pts[-1]["name"]["en"] == "Pandharpur"
    for p in pts:
        assert set(("name", "you", "lat", "lng", "temp_c", "code", "summary", "rain")) <= set(p)


def test_route_weather_endpoint(client):
    r = client.post("/api/route-weather", headers={"X-API-Key": "local-dev-key"},
                    json={"city": "Pune", "yatra": "pandharpur"})
    assert r.status_code == 200
    d = r.json()
    assert d["points"][0]["you"] is True and d["points"][-1]["name"]["en"] == "Pandharpur"
    # lat/lng origin also works
    r2 = client.post("/api/route-weather", headers={"X-API-Key": "local-dev-key"},
                     json={"origin": {"lat": 18.516, "lng": 73.856}, "yatra": "pandharpur"})
    assert r2.status_code == 200
    # missing origin → 400
    assert client.post("/api/route-weather", headers={"X-API-Key": "local-dev-key"},
                       json={"yatra": "pandharpur"}).status_code == 400
