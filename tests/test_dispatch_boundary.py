"""Exercise the real Moonraker POST path with synthetic DNS and a memory transport."""
import asyncio

import httpx
import pytest

from klippy.conversation import Conversation
from klippy.domain import Action, Intent
from klippy.moonraker import Moonraker
from klippy.safety import IN_FLIGHT, Rejected


@pytest.mark.parametrize("when", ["dns", "transport", "expired", "reconnect"])
async def test_revocation_at_dispatch_boundary(rig, monkeypatch, when):
    store, sim, engine, clock = rig
    reached, resume = asyncio.Event(), asyncio.Event()
    reads = 0

    async def resolve(fn, url):
        if reads == 6 and when != "transport":
            reached.set()
            await resume.wait()
        return ["127.0.0.1"]

    class SimulatedNetwork(httpx.MockTransport):
        def __bool__(self):
            return False  # Exercise endpoint lookup and still route all I/O into the simulator.

    async def handle(request):
        nonlocal reads
        if request.method == "GET":
            reads += 1
        elif when == "transport":
            reached.set()
            await resume.wait()
        return sim.handle(request)

    client = Moonraker(store.printers()[0], transport=SimulatedNetwork(handle))
    engine.clients = engine.limits.clients = lambda printer: client
    monkeypatch.setattr(asyncio, "to_thread", resolve)
    await engine.propose(Intent(action=Action.HEAT, printer_id="sim", params={"temperature": 90, "heater": 0}))
    token = engine.pending.token
    task = asyncio.create_task(engine.confirm(token))
    try:
        await asyncio.wait_for(reached.wait(), 3)
        if when == "expired":
            clock[0] += 60
        elif when == "reconnect":
            engine.limits.invalidate("sim")
        else:
            response = await Conversation(engine).hear("cancel that request")
            assert response == (IN_FLIGHT if when == "transport" else "Pending action canceled.")
    finally:
        resume.set()
    if when == "transport":
        assert "accepted" in await task
        assert len(sim.writes) == 1
    else:
        with pytest.raises(Rejected):
            await task
        assert sim.writes == []
    with pytest.raises(Rejected):
        await engine.confirm(token)
