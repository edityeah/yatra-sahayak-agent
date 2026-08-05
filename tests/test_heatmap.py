import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from agent import persistence as p


def test_occupancy_status_and_alerts():
    p.reset()

    async def run():
        for _ in range(900): await p.record_scan("PWK-temple", yatra="pandharpur")   # cap 800 → over
        for _ in range(300): await p.record_scan("PWK-jejuri", yatra="pandharpur")   # cap 500 → ok
        await p.create_sos("u", yatra="pandharpur", nature="faint", lat=17.6791, lng=75.3331)
        return await p.checkpoint_occupancy("pandharpur")

    h = asyncio.run(run())
    zones = {c["id"]: c for c in h["checkpoints"]}
    assert zones["PWK-temple"]["status"] == "over"
    assert zones["PWK-jejuri"]["status"] == "ok"
    assert zones["PWK-temple"]["incidents"] == 1          # SOS mapped to nearest checkpoint
    assert [a["id"] for a in h["alerts"]] == ["PWK-temple"]
    assert h["totals"]["scans"] == 1200 and h["totals"]["over"] == 1


def test_occupancy_only_counts_recent_window():
    p.reset()
    from datetime import datetime, timezone, timedelta
    # An old scan (2h ago) must not count in a 30-min window.
    p._SCANS.append({"checkpoint_id": "PWK-jejuri", "yatra": "pandharpur",
                     "created_at": datetime.now(timezone.utc) - timedelta(hours=2)})
    h = asyncio.run(p.checkpoint_occupancy("pandharpur", window_min=30))
    assert h["totals"]["scans"] == 0
