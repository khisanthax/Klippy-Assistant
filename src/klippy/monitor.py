from .domain import Snapshot
from .macros import discover
from .moonraker import ConnectionFailure


class Monitor:
    """Notification-only; deliberately has no reference to SafetyEngine or execute."""

    def __init__(self, store, clients, queries=None):
        self.store, self.clients = store, clients
        self.previous = {}
        self.cycles = 0
        self.mmu = {}
        self.semaphore = None
        self.queries = queries

    async def poll(self):
        import asyncio
        self.cycles += 1
        if self.semaphore is None:
            self.semaphore = asyncio.Semaphore(4)
        async def limited(printer):
            async with self.semaphore:
                return await one(printer)
        async def one(printer):
            try:
                snapshot = await self.clients(printer).snapshot()
            except (ConnectionFailure, KeyError, ValueError):
                snapshot = Snapshot(connected=False)
            previous = self.previous.get(printer.id)
            self.previous[printer.id] = snapshot
            reconnect = snapshot.connected and snapshot.ready and (
                previous is None or not previous.connected or not previous.ready)
            if self.queries:
                if not snapshot.connected or not snapshot.ready:
                    self.queries.invalidate(printer.id)
                else:
                    await self.queries.refresh(printer, force=reconnect or self.cycles % 12 == 0)
            if snapshot.connected and snapshot.ready and (
                previous is None or not previous.connected or not previous.ready or self.cycles % 12 == 0
            ):
                try:
                    config = await self.clients(printer).macro_config()
                    registry, _ = discover(config, self.store.macros(printer.id))
                    self.store.replace_macros(printer.id, registry)
                except (ConnectionFailure, KeyError, ValueError):
                    pass  # Writes independently revalidate discovery; a failed refresh grants no rights.
            mmu_fault = False
            if snapshot.connected:
                try:
                    mmu = await self.clients(printer).mmu_snapshot()
                    old_mmu = self.mmu.get(printer.id)
                    self.mmu[printer.id] = mmu
                    mmu_fault = mmu.fault and (old_mmu is None or not old_mmu.fault)
                except (ConnectionFailure, KeyError, ValueError, AttributeError):
                    self.mmu.pop(printer.id, None)
            else:
                self.mmu.pop(printer.id, None)
            code = None
            if not snapshot.connected and (previous is None or previous.connected):
                code = "disconnected"
            elif snapshot.connected and (not snapshot.ready or snapshot.state == "error") and (
                previous is None or previous.ready and previous.state != "error"
            ):
                code = "fault"
            elif snapshot.state == "paused" and (previous is None or previous.state != "paused"):
                code = "paused"
            if mmu_fault and code is None:
                code = "mmu_fault"
            if code:
                self.store.event(printer.id, code)
                return printer.name, code
            return None
        values = await asyncio.gather(*(limited(p) for p in self.store.printers() if p.approved))
        return [v for v in values if v]
