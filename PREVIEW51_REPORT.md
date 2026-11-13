# 0.5.1 preview — heating interpretation and explicit cancellation

Qualified engineering-preview scope at application source `2eabdfaee0bf0f189f18e5719714b0cbaec2ae63`.
No physical printer connections or heating actions
are used in development. Human microphone/room, broad continuous wake accuracy, actual fleet,
clean Windows desktop VM and actual 16 GB hardware acceptance remain open.

## Reproduction and correction

The owner's exact request was “Hey Klippy, can you set the Mercury 1 nozzle to 90 degrees
Celsius?”. In 0.5.0, a configured “Mercury One”/“M1” did not resolve spoken “Mercury 1”.
The deterministic heating matcher then failed on the residual name and used the LLM fallback.
“Unexpected parameters” is the safety guard for parameters attached to an action other than
HEAT/MACRO. A simulated model returning TEMPERATURES with heater/temperature parameters
reproduces the reported error without a write. The owner's actual model JSON was not recorded;
that specific output is a reproduction of the failure class, not a recovered owner trace.
Evidence: `benchmarks/preview51-initial-reproduction.json`.

Normalization now shares punctuation/possessive handling and bounded English number-word
parsing across printer names and heating recognition. Mercury One and Mercury 1 match only
configured labels; M1 must be configured as a name/alias. Collisions across printers are
rejected rather than guessed, including collisions in older saved configurations.
Heater/value/unit operands and command words are excluded from printer mentions. An alias F/C/nozzle/90 cannot
select a printer from a heating operand or strip its unit; an explicit “on F” still selects
that configured printer while preserving Fahrenheit conversion. The earlier unit-alias
collision is reproduced in `benchmarks/preview51-unit-alias-reproduction.json`.
Heating names are accepted only in a name position when removing that exact span leaves
a syntactically complete request or a heater request missing its target. Actual names such
as Nozzle One still work for switching, queries and named heating. A complete heating
request without a name keeps the selected printer; no target or unit is invented.

Set/heat/warm/bring instructions support polite wording, nozzle/hotend/hot end/extruder,
bed, printer placement, number words, decimal values and units. They enter the deterministic
HEAT path before temperature queries. Incomplete/ambiguous heating instructions ask for
one printer, heater and target; they never reach an LLM that might invent a value.
Temperature questions remain read-only.

No unit means Celsius, with no unit question. Celsius/C/degrees/degrees Celsius are accepted;
explicit Fahrenheit/F is converted with `(F - 32) * 5 / 9`. Confirmation shows the final
Celsius target. Conversion uses bounded decimal arithmetic and conservative float conversion
so a value just above a reviewed maximum cannot round down into the allowed range. The
selected printer, actual heater telemetry, fresh state and locally reviewed limits are
checked before a proposal and again at confirmation. Missing/malformed limits block heat.
Configured confirmation policies remain; no heating transmission is retried.

Invalid model action/parameter combinations are rejected independently in the model adapter,
conversation and SafetyEngine. They are never reclassified into an executable action.
Model HEAT values must also agree with an independent deterministic Celsius parse. A useful
spoken explanation replaces “Unexpected parameters”; bounded, sanitized error codes appear
only in in-memory Settings diagnostics with their reaction identifier, not normal speech.

## Cancellation and clarification

Only explicit cancellation or negative imperatives cancel a pending request: “No, don't do
that”, “Cancel that request”, “Never mind”, “Don't heat the nozzle”. Ordinary remarks such
as “I'm not sure why it didn't understand”, “That's not what I meant” and “I don't know
what happened” ask for clarification without reporting cancellation or sending an action.

An uncertain/corrective remark leaves an existing pending review present but suspends its
confirmation until a complete new request is stated. Old prompt completion cannot rearm it,
and voice/manual/direct confirmation cannot execute it. This avoids executing a request
the user has just questioned. A fresh request gets fresh validation and a new token; explicit
cancellation still discards the review. In-flight validation is invalidated during clarification.

## Automated coverage and qualification

Final local full suite: **510 passed**, all 408 prior regressions retained; Ruff passed.
Operand/name safety regressions are included. New tests cover the exact owner phrases and variations,
configured/colliding aliases, number words/units, Fahrenheit boundaries, missing heaters and
limits, query/action classification, invalid model output, explicit cancellation, clarification,
confirmation races/policies, Celsius review and single-use/no-retry behavior. All services
are simulated. No microphone recording or owner installation change is needed.

The packaged self-test additionally requires a 21-case heating/cancellation probe through
Conversation and SafetyEngine with a transport that forbids every HTTP write. Supported
requests must use zero LLM calls and leave zero writes/pending actions at completion.
Windows frozen/installed/offline/upgrade and memory qualification passed before publication.
Existing voice/query and negative-input gates remain; broad acoustic flags stay separate.
The same reviewed 57-file offline model pack is unchanged/outside Git.

[Windows run 43461231046, attempt 1](https://github.com/khisanthax/Klippy-Assistant/actions/runs/43461231046)
passed all jobs at the exact source above: **510 tests, zero failures/skips**, Ruff, frozen
startup/native probes, actual 0.5.0-to-0.5.1 upgrade, reinstall/legacy SQLite and settings
preservation, installed startup, offline runtime, memory accounting and uninstall preserving
data. Names/aliases, selected printer and response style survived upgrade/reinstall.
All Windows firewall profiles were enabled; app/runtime external egress was blocked.

All **21 command cases passed in each frozen/installed/memory-limited process**, with zero
HTTP writes, zero supported-request LLM calls and no pending action at completion. Each also
passed seven native query cases, six negative audio inputs with no accepted requests/sessions,
own echo/interruption and both preregistered single-attempt Hey wake-only/temperature cases.
The acknowledgement and unprefixed follow-up flow passed. Synthetic audio is not human
microphone accuracy evidence. Diagnostic counts are cumulative within each probe process.

Original broader full-voice flags remain **True / False / True** for frozen / installed /
memory. In the installed older bare-Klippy continuous status case, ASR produced “Clibby …”;
strict wake-prefix verification rejected it. That failed observation is retained unchanged in
`benchmarks/preview51-release-installed.json` and the aggregate. No phonetic-prefix, threshold
or negative-input gate was loosened. Broad/human wake reliability stays open. Earlier code
candidates 0588ed8/20bc35c were cancelled for unit/name correctness refinements before
publication, not retried to select a passing acoustic sample; reproductions remain committed.

The 8 GiB Windows runner (Intel Xeon Platinum 8370C) peaked at **1,958,084,608 bytes** process-tree
commit (about 1.82 GiB), three processes, **164.913 seconds** wall and 264.656 CPU seconds under
a 16 GiB job commit limit. This is not a clean Windows desktop VM or actual 16 GB host test.

Installer: `Klippy-Setup-0.5.1-preview.1.exe`, **1,489,751,540 bytes**, unsigned, about 1.39 GiB.

SHA-256: `c3b87742262793490f24511103db577d019fa8353043e3b1a756f636b460424f`.

CI artifact, checksum sidecar, installed-QA digest and local distribution copy agree.
Self-contained evidence: `benchmarks/preview51-release-qualification.json`; individual
frozen/installed/memory reports are alongside it. The same application identity upgrades
the per-user app while retaining settings and OS-vault credentials. Human microphone/room,
actual fleet/accessories, clean VM/actual 16 GB, sleep/resume and supervised physical heating
acceptance remain open. No owner installation was modified during this work.
