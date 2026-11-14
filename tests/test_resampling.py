import numpy as np
import pytest

from klippy.resampling import SpeechResampler


@pytest.mark.parametrize('source',[16000,24000,44100,48000])
def test_streaming_conversion_is_independent_of_chunk_boundaries(source):
    samples=np.random.default_rng(32).normal(0,.05,source).astype(np.float32)
    expected=SpeechResampler(source).push(samples,final=True)
    converter=SpeechResampler(source)
    parts=[converter.push(samples[i:i+137]) for i in range(0,len(samples),137)]
    parts.append(converter.finish())
    actual=np.concatenate(parts)
    assert len(actual)==16000 and np.max(np.abs(actual-expected))<1e-6
    assert len(converter.buffer)==0


@pytest.mark.parametrize('frequency',[300,1000,5000,10000])
def test_conversion_passband_and_antialias_response_against_analytic_tones(frequency):
    samples=np.sin(2*np.pi*frequency*np.arange(24000)/24000).astype(np.float32)
    actual=SpeechResampler(24000).push(samples,final=True)[100:-100]
    if frequency<8000:
        ideal=np.sin(2*np.pi*frequency*np.arange(16000)/16000)[100:-100]
        assert np.sqrt(np.mean((actual-ideal)**2))<.001
    else:
        assert np.sqrt(np.mean(actual**2))<.0001


def test_invalid_pcm_and_finished_converter_reject_without_silent_reinterpretation():
    converter=SpeechResampler(24000)
    with pytest.raises(ValueError):
        converter.push(np.array([float('nan')]))
    with pytest.raises(ValueError):
        converter.push(np.zeros((2,2)))
    converter.push(np.zeros(1),final=True)
    with pytest.raises(ValueError):
        converter.push(np.zeros(1))
