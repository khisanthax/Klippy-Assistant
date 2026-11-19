
import pytest

from klippy.voice_probe import qualify_preview_report


@pytest.mark.parametrize('defect',['summary','continuity','delivery'])
def test_audio_failures_block_preview_even_if_other_voice_gates_pass(defect, preview_evidence):
    report = preview_evidence
    qualify_preview_report(report)
    assert report['engineering_preview_passed']
    if defect=='summary':
        report['audio_quality']['passed']=False
    elif defect=='continuity':
        report['audio_quality']['checks']['chunk_invariance']=False
    else:
        report['audio_quality']['production_cached_pipeline']['passed']=False
    qualify_preview_report(report)
    assert not report['engineering_preview_passed']
