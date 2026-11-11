# Safety and security

Report security issues privately to the repository owner through GitHub. Do not include
tokens, actual device configuration, addresses, speech recordings or conversations in issues.

The application does not expose a remote control service. Runtime inference is local.
Approve only LAN printers you own/control. Windows account access is the trust boundary;
speaker identity is not authentication. Vault protection does not replace printer access control.

Never approve a macro without inspecting its full behavior and callees. Descriptions and
comments are untrusted. Macro approval can allow hazardous activity; the assistant cannot
prove arbitrary Jinja/G-code safe. Unknown definitions and dynamic parameters stay blocked.

Confirmations expire, bind exact requests and recheck state/permissions. A cancellation
affects pending requests only, never retracts a physical action already transmitted. Writes
are never retried automatically. An unknown transmission outcome requires checking the printer.

Monitoring never initiates a corrective command. Voice and software emergency control do
not replace physical emergency mechanisms. Use the printer's physical controls when needed.

Preview limitations: no qualified acoustic echo cancellation, no signed installer, no stable
model payload, no supervised actuation validation. Read RELEASE_CHECKLIST before promotion.
