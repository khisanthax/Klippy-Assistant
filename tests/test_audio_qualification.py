import json
from pathlib import Path

import pytest

from klippy.voice_probe import qualify_preview_report


@pytest.mark.parametrize('defect',['summary','continuity','delivery'])
def test_audio_failures_block_preview_even_if_other_voice_gates_pass(defect):
    report=json.loads((Path(__file__).parents[1]/'benchmarks/preview6-release-frozen.json').read_text(encoding='utf-8'))
    report['limits_probe'] = {'passed':True,'printer_writes':0,'cases':[{'passed':True} for _ in range(8)]}
    report['audio_quality']={'passed':True,'checks':{key:True for key in (
        'original_is_finite_unclipped','callback_chunks_match_original','converted_length',
        'chunk_invariance','antialias_rejection','render_preserves_converted_pcm',
        'buffered_generation_has_no_starvation','non_silent_render_receipt')},
        'production_cached_pipeline':{'passed':True}}
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
