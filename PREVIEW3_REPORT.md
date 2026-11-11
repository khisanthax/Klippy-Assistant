# 0.3.0 preview: voice usability, fleet monitoring and recovery

Engineering preview, unsigned, CPU only. Hardware and clean Windows desktop VM gates
remain open. No physical printer commands were used for development or qualification.

## Changes

- A shared follow-up session remains active through ASR, interpretation and playback.
  The default 30-second window restarts after an exchange completes. Wake interruption,
  bounded queues, own-speech rejection, exact tokens and stale-generation rejection remain.
  New requests cancel stale interpretation tasks without canceling safety-engine transmissions.
- Kokoro callbacks enqueue PCM during generation. A process-local 32 MiB/32-response
  cache avoids repeated synthesis. Models remain loaded between requests.
- A spoken confirmation is unarmed until its exact prompt drains through playback plus
  the DAC/echo-tail allowance. The application defaults to a configurable 30-second response
  window, with a 180-second total lifetime. Interrupted/failed prompts cancel their token;
  muted responses start the window from text delivery. Stale completions cannot arm replacements.
- Temperature and progress questions use deterministic intents and direct Moonraker objects.
  Nozzle/bed queries name the requested heater; absent values are explicitly unavailable.
- Monotonic, bounded in-memory diagnostics cover wake, VAD, capture/ASR queues, ASR,
  deterministic interpretation, LLM startup/queue/inference, Moonraker, normalization,
  synthesis, playback queue and first render. First-audible timing is an estimate using
  device delay, not a microphone measurement. Settings contains a simulated reaction test.
- Up to four approved printers are polled concurrently. Fleet rows show per-printer
  progress and Happy Hare state/tool/gate. Capability discovery avoids assuming an MMU.
  Versioned MMU state fields normalize into deduplicated notifications only; Klippy never
  diagnoses a specific clog from an unspecified pause and never runs an automatic repair.
- Approved macro names/aliases support deterministic verb synonyms and explicit reviewed
  numeric parameters. Unknown/duplicate numeric parameters are rejected. Body similarity
  and rename warnings never transfer approval. Review shows the prior/current definition diff.
- Confirmation prompts for pause/resume/cancel/home/heat can be disabled individually,
  with warnings and fresh validation immediately before a single transmission. Enrollment,
  selection, state, heater limits and policy bindings remain mandatory. Macros and critical
  operations always require confirmation. Defaults enable every confirmation. Settings
  supports explicit per-printer verified heater-limit review; unknown bounds block heating.
- Scrollable settings, companion visibility/duration and remembered position, validated
  schedules, versioned preference backup and transactional recovery are implemented.
  Restore first creates an online SQLite backup, revokes device/macro approvals, resets
  confirmation bypasses and leaves the microphone off. Credentials are never exported.

## Measured latency

Same CPU, same models and phrases; two original runs and first/cached streamed runs.
This measures PCM availability, not physical audibility or full human speech latency.

| Response | Original first PCM | Streamed first PCM | Cached first PCM |
|---|---:|---:|---:|
| Temperatures | 8.273–8.349 s | 1.935 s | <1 ms |
| Confirmation | 11.538–11.606 s | 2.051 s | <1 ms |

Root causes were independent clocks expiring during work, confirmation expiry beginning
at proposal, and full-response synthesis before playback. Deterministic natural queries
also avoid invoking the LLM for common status questions. These observations do not
establish microphone accuracy or a latency percentile across different computers.

Repeat with `python scripts/latency_probe.py --output local/latency-after.json`.
The baseline was captured from the original `SherpaBackend.synthesize` before modifications.
Raw numeric evidence is in `benchmarks/preview3-latency-*.json`.
The real-model delivery probe additionally passed uncached/cached prompt playback into a
simulated PCM sink: neither token armed early; both received a full 30-second response
window after delivery. See `benchmarks/preview3-delivery.json`; repeat with
`python scripts/delivery_probe.py`. That sink includes OS scheduling overhead and does
not measure a physical speaker.

## Qualification and remaining gates

Source tests preserve the original 99 cases and add follow-up, slow inference/playback,
confirmation lifecycle, multiple-printer MMU, policy-toggle, macro and recovery regressions.
The complete real-model synthetic integration probe passed with zero simulated printer writes.
Build tooling runs Ruff, tests, frozen startup and frozen real-model integration before
creating an installer. The installer harness supports an actual 0.2 → 0.3 upgrade,
reinstall and preservation of isolated SQLite data, installed voice checks and uninstall.
The dedicated CI job repeats installation on a fresh Windows runner with executable-specific
external-egress firewall blocks. Final run IDs and artifact checksums belong in LOGBOOK/release notes.

`scripts/performance_probe.ps1` applies a 16 GiB Windows Job Object commit limit to the
frozen app and inherited language runtime, measuring peak memory, CPU time and wall time.
That is not equivalent to a machine with 16 GB of total physical memory.

Human microphone/room accuracy, actual fleet authentication and accessory behavior,
supervised hazardous actions, clean Windows desktop VM/no-network acceptance, 16 GB total
RAM performance, sleep/resume and extended desktop soak remain open. The current host
has about 64 GiB of RAM and no installed Windows Sandbox/Hyper-V/VirtualBox runner.
Stable v1.0 is blocked until the release checklist gates have evidence.

Status normalization follows the upstream [Happy Hare printer-variable reference](https://moggieuk.github.io/Happy-Hare-Doc/Reference-Printer-Variables/).
Memory accounting uses Microsoft's [Job Object extended limits](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_extended_limit_information).
