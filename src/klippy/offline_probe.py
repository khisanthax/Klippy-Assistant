"""Process-wide Python egress denial for isolated qualification subprocesses only."""
import sys


def deny_external_network():
    def audit(event, args):
        if event == "socket.getaddrinfo":
            if args[0] not in {"localhost", "127.0.0.1", "::1"}:
                raise RuntimeError("Offline qualification forbids external DNS")
        elif event == "socket.connect":
            address = args[1]
            if not isinstance(address, tuple) or address[0] not in {"127.0.0.1", "::1"}:
                raise RuntimeError("Offline qualification forbids external connections")
    sys.addaudithook(audit)
