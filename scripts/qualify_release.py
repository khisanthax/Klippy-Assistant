"""Recheck downloaded artifacts from a single Windows workflow run."""
import argparse
import hashlib
import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from klippy.preview_contract import FEATURE_CHECKS, ORB_CHECKS, REVISION, WAKE_CHECKS, qualify_preview_report


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def checks(section, names):
    return section["passed"] is True and all(section["checks"].get(name) is True for name in names)


def hash_matches(path, receipt):
    with path.open('rb') as data:
        return receipt['report_sha256'][path.name] == hashlib.file_digest(data, 'sha256').hexdigest()


def verify_native(folder, prefix):
    receipt = read(folder / ("frozen-build.json" if prefix == "frozen" else "results.json"))
    if not all(hash_matches(folder / f"{prefix}-{name}", receipt)
               for name in ("voice.json", "orb.json", "wake.json", "smoke.txt")):
        return False
    voice = read(folder / f"{prefix}-voice.json")
    if voice.get("qualification_revision") != REVISION:
        return False
    qualify_preview_report(voice)
    orb = read(folder / f"{prefix}-orb.json")
    wake = read(folder / f"{prefix}-wake.json")
    positive = {(phrase, sid, speed, True) for phrase in ("Hey Clippy", "Clippy")
                for sid in (0, 1, 3) for speed in (.85, 1, 1.15)}
    negative = {(phrase, 0, 1, False) for phrase in
                ("Hey puppy", "Hey creepy", "Hey copy", "Klipper", "Hey Clipper", "Hey Cuppy", "Hey Crippy")}
    cases = wake["cases"]
    observed = {(r["synthetic_phrase"], r["voice"], r["speed"], r["positive"]) for r in cases}
    return (voice["engineering_preview_passed"] and checks(orb, ORB_CHECKS)
            and checks(orb["conversation_features"], FEATURE_CHECKS) and checks(wake, WAKE_CHECKS)
            and observed == positive | negative and len(cases) == len(observed)
            and all(r["recovered_wake_only"] is False for r in cases if not r["positive"])
            and (folder / f"{prefix}-smoke.txt").read_text().strip() == "Startup and shutdown completed successfully.")


def evaluate(root, source, run, attempt):
    status = {}
    manifest = {"schema": REVISION, "source_sha": source, "run_id": run, "run_attempt": attempt,
                "gates": status, "qualified_for_publication": False}
    def gate(name, test):
        try:
            status[name] = "passed" if test() else "failed"
        except FileNotFoundError:
            status[name] = "missing"
        except (KeyError, IndexError, StopIteration, TypeError, ValueError, OSError, ET.ParseError):
            status[name] = "failed"

    frozen = root / "frozen-qualification-diagnostics"
    def installer():
        setups = list((root / "klippy-engineering-preview").glob("Klippy-Setup-*.exe"))
        if not setups:
            raise FileNotFoundError("Installer missing")
        setup, = setups
        with setup.open("rb") as data:
            digest = hashlib.file_digest(data, "sha256").hexdigest()
        manifest.update(installer=setup.name, installer_sha256=digest)
        return setup.with_suffix(".exe.sha256").read_text().split() == [digest, setup.name]

    def identity(receipt):
        return (receipt["source_sha"] == source and re.fullmatch("[a-f0-9]{40}", source)
                and receipt["run_id"] == run and run.isdigit() and receipt["run_attempt"] == attempt
                and attempt.isdigit() and receipt["installer_sha256"] == manifest["installer_sha256"])

    def tests():
        suite = ET.parse(root / "test-results" / "test-results.xml").getroot().find("testsuite")
        return (suite is not None and int(suite.get("tests")) >= 886 and
                all(int(suite.get(key)) == 0 for key in ("errors", "failures", "skipped")))

    gate("source_tests", tests)
    gate("installer_checksum", installer)
    gate("frozen_identity", lambda: identity(read(frozen / "frozen-build.json")))
    gate("frozen_native", lambda: verify_native(frozen, "frozen"))
    for consent in ("on", "off"):
        base = root / ("installer-qualification-evidence-" + consent)
        folder = base / "installer-qa"
        def installed():
            receipt = read(folder / "results.json")
            return (identity(receipt) and receipt["status"] == "passed" and receipt["consent"] == consent
                    and receipt["cross_version_upgrade"] is True and receipt["external_network_blocked"] is True
                    and re.fullmatch("[a-f0-9]{64}", receipt["preserved_profile_sha256"])
                    and receipt["executable_sha256"] == read(frozen / "frozen-build.json")["executable_sha256"])
        gate("offline_upgrade_reinstall_uninstall_consent_" + consent, installed)
        gate("installed_native_consent_" + consent, lambda: verify_native(folder, "installed"))
        if consent == "on":
            def memory():
                receipt = read(folder / "results.json")
                if not all(hash_matches(base / name, receipt) for name in ("performance-budget.json", "performance-voice.json")):
                    return False
                perf = read(base / "performance-budget.json")
                voice = read(base / "performance-voice.json")
                if voice.get("qualification_revision") != REVISION:
                    return False
                qualify_preview_report(voice)
                return (voice["engineering_preview_passed"] and perf["passed"] is True
                        and perf["memory_budget_gib"] == 16 and 0 < perf["peak_job_commit_bytes"] <= 16 * 1024**3
                        and perf["peak_active_processes"] >= 2 and read(folder / "results.json")["performance_budget_test"] is True)
            gate("installed_memory_budget", memory)
    manifest["qualified_for_publication"] = all(value == "passed" for value in status.values())
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("artifacts", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest = evaluate(args.artifacts, os.environ["GITHUB_SHA"], os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"])
    args.output.write_text(json.dumps(manifest, indent=2) + "\n")
    raise SystemExit(0 if manifest["qualified_for_publication"] else 1)
