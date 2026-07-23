"""Activity nodes — one focused module per NDMA activity (spec §5).

Plan 2 fills in each module with real behaviour; the graph binds to
ACTIVITY_NODES (names unchanged from Plan 1).
"""
from __future__ import annotations

from agent.nodes.activities.weather import weather
from agent.nodes.activities.advisory import advisory
from agent.nodes.activities.logistics import logistics
from agent.nodes.activities.helpline import helpline
from agent.nodes.activities.drills_sos import drills_sos
from agent.nodes.activities.signage import signage
from agent.nodes.activities.registration import registration

ACTIVITY_NODES = {
    "weather": weather,
    "advisory": advisory,
    "logistics": logistics,
    "helpline": helpline,
    "drills_sos": drills_sos,
    "signage": signage,
    "registration": registration,
}
