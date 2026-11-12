from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
from urllib.parse import urlencode, urlsplit

import httpx
from websockets.asyncio.client import connect

from .diagnostics import timings
from .domain import Printer, Snapshot


class ConnectionFailure(Exception):
    """Intentionally excludes endpoints, credentials and server response bodies."""


def lan_addresses(url):
    parsed = urlsplit(url)
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80),
                                   type=socket.SOCK_STREAM)
    result = []
    for row in addresses:
        ip = ipaddress.ip_address(row[4][0])
        allowed = ip.is_loopback or ip.is_link_local or any(ip in network for network in (
            ipaddress.ip_network("10.0.0.0/8"), ipaddress.ip_network("172.16.0.0/12"),
            ipaddress.ip_network("192.168.0.0/16"), ipaddress.ip_network("fc00::/7")))
        if not allowed or ip.is_multicast or ip.is_unspecified or str(ip) == "169.254.169.254":
            raise ConnectionFailure("Only local/private printer endpoints are allowed")
        result.append(str(ip))
    return result


class Moonraker:
    def __init__(self, printer: Printer, api_key=None, transport=None):
        self.printer = printer
        self.api_key = api_key
        self.transport = transport  # Injected simulator; no real DNS/network in unit tests.
        self.status_observer = None

    async def request(self, method, path, payload=None):
        try:
            # Pin DNS result to avoid rebinding between validation and connection.
            parsed = urlsplit(self.printer.url)
            if self.transport:
                endpoint = self.printer.url
            else:
                addresses = await asyncio.to_thread(lan_addresses, self.printer.url)
                host = f"[{addresses[0]}]" if ":" in addresses[0] else addresses[0]
                endpoint = f"{parsed.scheme}://{host}:{parsed.port or (443 if parsed.scheme == 'https' else 80)}"
            headers = {"Host": parsed.netloc}
            if self.api_key:
                headers["X-Api-Key"] = self.api_key
            async with httpx.AsyncClient(timeout=6, trust_env=False, follow_redirects=False,
                                         transport=self.transport) as client:
                with timings.span("moonraker"):
                    response = await client.request(method, endpoint + path, json=payload, headers=headers)
                response.raise_for_status()
                value = response.json()
                if not isinstance(value, dict) or "error" in value or "result" not in value:
                    raise ConnectionFailure("Printer rejected request")
                return value["result"]
        except (httpx.HTTPError, ValueError, KeyError, OSError):
            # Do not retry writes, print exception bodies, or forward server diagnostics to logs.
            raise ConnectionFailure("Printer unavailable, unauthorized, or response invalid") from None

    async def snapshot(self):
        import time
        acquired = time.monotonic()
        value = await self.request("GET", "/printer/objects/query?webhooks&print_stats&virtual_sdcard&extruder&heater_bed")
        if self.status_observer:
            self.status_observer(value, acquired)
        status = value["status"]
        web = status.get("webhooks", {})
        return Snapshot(connected=True, ready=web.get("state") == "ready",
                        state=str(status.get("print_stats", {}).get("state", "unknown")),
                        progress=(float(status["virtual_sdcard"]["progress"])
                                  if status.get("virtual_sdcard", {}).get("progress") is not None else None),
                        temperatures={name: float(status[name]["temperature"])
                                      for name in ("extruder", "heater_bed") if "temperature" in status.get(name, {})},
                        message=str(web.get("state_message", ""))[:500])

    async def mmu_snapshot(self):
        from .mmu import MmuStatus, normalize
        objects = await self.request("GET", "/printer/objects/list")
        if "mmu" not in objects.get("objects", []):
            return MmuStatus()
        value = await self.request("GET", "/printer/objects/query?mmu")
        return normalize(value.get("status", {}).get("mmu"))

    async def macro_config(self):
        result = await self.request("GET", "/printer/objects/query?configfile")
        return result["status"]["configfile"].get("config", {})

    async def execute(self, intent, script=None):
        from .domain import Action
        paths = {Action.PAUSE: "/printer/print/pause", Action.RESUME: "/printer/print/resume",
                 Action.CANCEL: "/printer/print/cancel", Action.EMERGENCY: "/printer/emergency_stop"}
        if intent.action in paths:
            return await self.request("POST", paths[intent.action])
        if script is None:
            raise ValueError("No validated command")
        return await self.request("POST", "/printer/gcode/script", {"script": script})

    async def notifications(self):
        """Read-only subscription. Actions never originate from this channel."""
        parsed = urlsplit(self.printer.url)
        addresses = await asyncio.to_thread(lan_addresses, self.printer.url)
        host = f"[{addresses[0]}]" if ":" in addresses[0] else addresses[0]
        scheme = "wss" if parsed.scheme == "https" else "ws"
        port = parsed.port or (443 if scheme == "wss" else 80)
        token = None
        if self.api_key:
            token = await self.request("GET", "/access/oneshot_token")
        suffix = "?" + urlencode({"token": token}) if token else ""
        async with connect(f"{scheme}://{host}:{port}/websocket{suffix}",
                           proxy=None, open_timeout=6, max_size=2**20) as ws:
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "printer.objects.subscribe",
                                      "params": {"objects": {"webhooks": None, "print_stats": None}}}))
            async for message in ws:
                value = json.loads(message)
                if value.get("method", "").startswith("notify_"):
                    yield value
