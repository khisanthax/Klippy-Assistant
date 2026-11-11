from .domain import Snapshot
from .moonraker import ConnectionFailure


class Monitor:
    """Notification-only; deliberately has no reference to SafetyEngine or execute."""

    def __init__(self, store, clients):
        self.store, self.clients = store, clients
        self.previous = {}

    async def poll(self):
        import asyncio
        async def one(printer):
            try:
                snapshot = await self.clients(printer).snapshot()
            except (ConnectionFailure, KeyError, ValueError):
                snapshot = Snapshot(connected=False)
            previous = self.previous.get(printer.id)
            self.previous[printer.id] = snapshot
            code = None
            if not snapshot.connected and (previous is None or previous.connected):
                code = "disconnected"
            elif snapshot.connected and not snapshot.ready and (previous is None or previous.ready):
                code = "fault"
            elif snapshot.state == "paused" and (previous is None or previous.state != "paused"):
                code = "paused"
            if code:
                self.store.event(printer.id, code)
                return printer.name, code
            return None
        values = await asyncio.gather(*(one(p) for p in self.store.printers() if p.approved))
        return [v for v in values if v]
