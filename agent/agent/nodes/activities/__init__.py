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
from agent.nodes.activities.lost_found import lost_found
from agent.nodes.activities.grievance import grievance
from agent.nodes.activities.darshan import darshan
from agent.nodes.activities.accommodation import accommodation
from agent.nodes.activities.langar import langar
from agent.nodes.activities.amenity import amenity
from agent.nodes.activities.palkhi import palkhi
from agent.nodes.activities.parking import parking

ACTIVITY_NODES = {
    "weather": weather,
    "advisory": advisory,
    "logistics": logistics,
    "helpline": helpline,
    "drills_sos": drills_sos,
    "signage": signage,
    "registration": registration,
    "lost_found": lost_found,
    "grievance": grievance,
    "darshan": darshan,
    "accommodation": accommodation,
    "langar": langar,
    "amenity": amenity,
    "palkhi": palkhi,
    "parking": parking,
}
