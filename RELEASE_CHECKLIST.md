# Release gates

Stable release is blocked until every applicable item has evidence.

- [x] Private repository pushed; CI passes on Windows.
- [ ] Current LOGBOOK, roadmap, architecture, user guide, license notices.
- [x] Application launches and closes cleanly from installed package (development host).
- [ ] Complete local speech and LLM assets with reviewed redistribution rights, versions,
      immutable sources, checksums and included license texts.
- [ ] Verified Klippy wake word on actual microphone; no unrelated substitute.
- [ ] Natural ASR/TTS, clarification, conversation expiry and hands-free interruption.
- [ ] Default audio device changes and unavailable devices tested.
- [ ] Active printer persistence, enrollment/authentication and multi-printer operation.
- [ ] Macro discovery/changes/renames/conflicts/parameters validated on fleet.
- [ ] Safety suite and supervised hazardous operation tests pass.
- [ ] Fault monitoring never controls hardware; Happy Hare faults tested where available.
- [ ] Companion visibility/animation/tray and listening schedule verified.
- [ ] CPU-only benchmark results with host specifications.
- [ ] Single installer with all required runtime/model assets; no post-install downloads.
- [ ] Clean-machine install/upgrade/uninstall and offline runtime verified.
- [ ] No critical/high defects; limitations documented; release artifact checksums.
- [x] Digital signing status accurate (currently unsigned).

Engineering preview packages may omit the voice pack only if labeled explicitly. A preview
must never claim that a mock test satisfies hardware, acoustic or clean-machine gates.
