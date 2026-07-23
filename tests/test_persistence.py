import sys, os, asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agent"))
from agent import persistence as p


def setup_function():
    p.reset()


def test_user_state_roundtrip_memory():
    async def go():
        await p.set_user_state("u1", language="mr", active_yatra="kumbh")
        s = await p.get_user_state("u1")
        assert s["language"] == "mr" and s["active_yatra"] == "kumbh"
    asyncio.run(go())


def test_partial_user_state_update_preserves_other_field():
    async def go():
        await p.set_user_state("u2", language="en")
        await p.set_user_state("u2", active_yatra="pandharpur")
        s = await p.get_user_state("u2")
        assert s["language"] == "en" and s["active_yatra"] == "pandharpur"
    asyncio.run(go())


def test_registration_and_sos_memory():
    async def go():
        yid = await p.create_registration("u1", yatra="pandharpur", name="Asha",
                                          phone="+9199", group_name="Dindi 5",
                                          emergency_contact="+9198", medical_flags="elderly")
        assert yid.startswith("PWARI-")
        reg = await p.get_registration_for_user("u1")
        assert reg["name"] == "Asha" and reg["yatra_id"] == yid
        sid = await p.create_sos("u1", yatra="pandharpur", yatra_id=yid,
                                 location="Wakhari halt", nature="medical")
        assert sid
        events = await p.list_sos()
        assert any(e["id"] == sid and e["user_id"] == "u1" for e in events)
    asyncio.run(go())


def test_kumbh_prefix():
    async def go():
        yid = await p.create_registration("u3", yatra="kumbh", name="X", phone="", group_name="", emergency_contact="", medical_flags="")
        assert yid.startswith("KUMBH-")
    asyncio.run(go())
