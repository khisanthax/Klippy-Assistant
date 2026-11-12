import json
from pathlib import Path

import pytest

from klippy.voice_probe import qualify_report


def observed_report():
    return json.loads((Path(__file__).parents[1] / "benchmarks/preview3-embedded-raw-miss.json").read_text())


def test_actual_composite_interruption_is_distinct_from_raw_keyword_recall():
    report = observed_report()
    # This real CI report accepted the request and interrupted successfully despite
    # one auxiliary KWS-only embedded-phrase miss. The miss must remain visible.
    qualify_report(report)
    assert report["passed"] and report["gates"]["verified_interruption"]
    assert report["raw_embedded_keyword"]["detected"] == 3
    assert report["raw_embedded_keyword"]["total"] == 4
    assert report["raw_embedded_keyword"]["misses"][0]["phrase"] == "Klippy stop talking"


@pytest.mark.parametrize("defect", ["wake", "negative", "pipeline", "interruption", "echo", "write", "language"])
def test_qualification_keeps_all_functional_and_safety_gates_mandatory(defect):
    report = observed_report()
    if defect in {"wake", "negative"}:
        phrase = "Klippy" if defect == "wake" else "clipper"
        next(case for case in report["wake_cases"] if case["phrase"] == phrase)["detected"] = defect == "negative"
    elif defect == "pipeline":
        report["pipeline_transcripts"] = []
    elif defect == "interruption":
        report["barge_requests"] = []
    elif defect == "echo":
        report["own_echo_wakes"] = 1
    elif defect == "write":
        report["printer_writes"] = 1
    else:
        report["llm_intent"]["action"] = "home"
    qualify_report(report)
    assert not report["passed"]
