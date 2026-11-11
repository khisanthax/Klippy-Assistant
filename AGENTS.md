# Klippy development continuity

Read LOGBOOK.md before resuming. The full product brief is in docs/PROJECT_BRIEF.md.
ROADMAP.md tracks incomplete phases; RELEASE_CHECKLIST.md defines stable acceptance.
Update LOGBOOK.md after significant work with actual tests, blockers and the next action.

Use the deterministic safety engine as the only application write path. Never execute
LLM-generated G-code, retry uncertain consequential commands, or give monitoring any
corrective-action authority. Add a regression for every safety defect.

Use simulated Moonraker services for automated tests. Real movement, heating, pause,
cancellation, emergency stopping or configuration modification requires a separate
supervised user-authorized test. For read-only Mercury work use the configured mercury
SSH alias; never request/expose keys, passwords or tokens. Do not commit real printer
addresses/configurations, audio recordings, personal conversations or credentials.

Run tests and Ruff; verify frozen startup and installer behavior after packaging changes.
Keep models out of Git. Record provenance/checksums and independently qualify model
licenses. An integrity manifest alone is not evidence of accuracy or redistribution rights.
Do not claim stable v1.0 until hardware, acoustic, clean-machine and offline gates pass.
