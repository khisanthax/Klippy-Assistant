import socket

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf


class Discovery(ServiceListener):
    """Only advertisements. Discovery never enrolls or connects to a device."""

    def __init__(self):
        self.found = {}
        self.zc = Zeroconf()
        self.browser = ServiceBrowser(self.zc, "_moonraker._tcp.local.", self)

    def add_service(self, zc, kind, name):
        info = zc.get_service_info(kind, name, timeout=1000)
        if info:
            addresses = info.parsed_addresses(socket.AF_INET)
            if addresses:
                self.found[name] = f"http://{addresses[0]}:{info.port}"

    def update_service(self, zc, kind, name):
        self.add_service(zc, kind, name)

    def remove_service(self, zc, kind, name):
        self.found.pop(name, None)

    def close(self):
        self.browser.cancel()
        self.zc.close()
