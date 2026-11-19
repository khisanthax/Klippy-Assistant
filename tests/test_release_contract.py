import importlib.util
import sqlite3
from pathlib import Path

import pytest

from klippy.preview_contract import qualify_preview_report


@pytest.mark.parametrize("missing", ["dialogue", "audio_quality", "followup_capture_count", "heat_fix_probe",
                                     "wake_cases", "query_catalog", "negative_composite", "limits_probe", "gates"])
def test_absent_evidence_blocks_preview(preview_evidence, missing):
    preview_evidence.pop(missing)
    qualify_preview_report(preview_evidence)
    assert not preview_evidence["engineering_preview_passed"]


@pytest.mark.parametrize("section", ["query_catalog", "limits_probe", "heat_fix_probe", "negative_composite"])
def test_duplicated_case_cannot_replace_another(preview_evidence, section):
    group = preview_evidence[section]
    cases = group if isinstance(group, list) else group["cases"]
    cases[1] = cases[0]
    qualify_preview_report(preview_evidence)
    assert not preview_evidence["engineering_preview_passed"]


@pytest.mark.parametrize("consent", [False, True])
def test_installer_qa_detects_profile_loss(tmp_path, consent):
    spec = importlib.util.spec_from_file_location("installer_settings",
        Path(__file__).parents[1] / "scripts" / "installer_settings.py")
    qa = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qa)
    profile = tmp_path / "fixture"
    qa.prepare(profile, consent)
    before = qa.snapshot(profile, consent)
    database = profile / ("conversation-history.sqlite" if consent else "settings.sqlite")
    with sqlite3.connect(database) as db:
        if consent:
            db.execute("UPDATE turns SET data='{}'")
        else:
            db.execute("UPDATE settings SET value='{}' WHERE key='conversation_log'")
    db.close()
    assert qa.snapshot(profile, consent) != before
    database.unlink()
    with pytest.raises(sqlite3.OperationalError):
        qa.snapshot(profile, consent)
    assert not database.exists()


@pytest.mark.parametrize("consent", ["on", "off"])
def test_boot_previous_profile_preserves_seeded_rows(tmp_path, consent):
    import os
    import subprocess
    import sys
    import uuid

    spec = importlib.util.spec_from_file_location("installer_settings",
        Path(__file__).parents[1] / "scripts" / "installer_settings.py")
    qa = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(qa)
    base = tmp_path / "installer-qa" / ("profile-" + consent + "-" + uuid.uuid4().hex)
    profile = base / "KlippyAssistant"
    qa.prepare(profile, consent == "on")
    receipt = qa.snapshot(profile, consent == "on")
    subprocess.run([sys.executable, "-m", "klippy.app", "--smoke-test"], timeout=25, check=True,
                   env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "LOCALAPPDATA": str(base),
                        "KLIPPY_SMOKE_QA_PROFILE": str(base)})
    assert qa.snapshot(profile, consent == "on") == receipt


def test_final_manifest_binds_every_runtime_to_one_installer(tmp_path, preview_evidence):
    import hashlib
    import json
    import shutil

    project = Path(__file__).parents[1]
    spec = importlib.util.spec_from_file_location("qualify_release", project / "scripts/qualify_release.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source, run, attempt = "a" * 40, "123", "1"
    folder = tmp_path / "klippy-engineering-preview"
    folder.mkdir()
    setup = folder / "Klippy-Setup-synthetic.exe"
    setup.write_bytes(b"fixture")
    digest = hashlib.sha256(setup.read_bytes()).hexdigest()
    setup.with_suffix(".exe.sha256").write_text(digest + "  " + setup.name)
    identity = dict(source_sha=source, run_id=run, run_attempt=attempt,
                    executable_sha256="b" * 64, installer_sha256=digest)
    qualify_preview_report(preview_evidence)
    voice = json.dumps(preview_evidence)
    def native(folder, prefix):
        folder.mkdir(parents=True)
        (folder / (prefix + "-voice.json")).write_text(voice)
        (folder / (prefix + "-smoke.txt")).write_text("Startup and shutdown completed successfully.")
        for kind in ("orb", "wake"):
            shutil.copy(project / f"benchmarks/preview8-local-frozen-{kind}.json", folder / f"{prefix}-{kind}.json")
    frozen = tmp_path / "frozen-qualification-diagnostics"
    native(frozen, "frozen")
    def hashes(folder, pattern):
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob(pattern) if p.is_file()}
    (frozen / "frozen-build.json").write_text(json.dumps(dict(identity, report_sha256=hashes(frozen, "frozen-*"))))
    tests = tmp_path / "test-results"
    tests.mkdir()
    (tests / "test-results.xml").write_text('<testsuites><testsuite tests="917" failures="0" errors="0" skipped="0"/></testsuites>')
    for consent in ("on", "off"):
        base = tmp_path / ("installer-qualification-evidence-" + consent)
        installed = base / "installer-qa"
        native(installed, "installed")
        result = dict(identity, status="passed", consent=consent, preserved_profile_sha256="c" * 64,
                      cross_version_upgrade=True, external_network_blocked=True, performance_budget_test=True)
        (installed / "results.json").write_text(json.dumps(result))
        if consent == "on":
            (base / "performance-voice.json").write_text(voice)
            (base / "performance-budget.json").write_text(json.dumps(dict(
                passed=True, memory_budget_gib=16, peak_job_commit_bytes=1024, peak_active_processes=2)))
        result['report_sha256'] = {**hashes(installed, "installed-*"), **hashes(base, "performance-*")}
        (installed / "results.json").write_text(json.dumps(result))
    def verdict():
        return module.evaluate(tmp_path, source, run, attempt)
    assert verdict()["qualified_for_publication"]
    result["source_sha"] = "d" * 40
    (installed / "results.json").write_text(json.dumps(result))
    assert not verdict()["qualified_for_publication"]
    setup.write_bytes(b"replacement")
    assert verdict()["gates"]["installer_checksum"] == "failed"
    (installed / "installed-voice.json").unlink()
    assert verdict()["gates"]["installed_native_consent_off"] == "missing"
