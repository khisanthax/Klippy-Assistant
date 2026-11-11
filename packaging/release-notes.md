Klippy Assistant 0.1.0 engineering preview

Includes the Windows companion, approved-printer management, macro review, independent
command safety, confirmations, listening schedules and notification-only monitoring.

78 automated tests pass locally. Windows test CI and source/frozen startup checks have
passed. Development-host installer checks cover per-user install, same-version reinstall,
preserved isolated settings, installed launch and uninstall. See RELEASE_REPORT.md for
scoped measurements and evidence; this is not clean-machine qualification.

Voice is disabled by default. This installer does not include a redistribution-qualified
speech/LLM model payload. Experimental local CPU-only inference has been exercised, but
the primary short Klippy wake phrase failed its synthetic probe and real microphone
accuracy is unverified. Hands-free interruption and optional speaker enrollment are absent.

No consequential printer actions were tested on hardware. Stable v1.0 is not complete.
This package is unsigned. Runtime uses no cloud AI and does not download models.

Installation: run Klippy-Setup-0.1.0-preview.1.exe as a normal Windows user, then open
Klippy from Start. Read README.md before approving printers/macros. Settings and vault
credentials are preserved on uninstall; README describes backup and manual data removal.
Verify the adjacent SHA-256 file. All eight phases and remaining acceptance work are
tracked in repository milestones/issues.
