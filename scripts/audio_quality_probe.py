"""Synthetic Kokoro PCM audit. Never captures a microphone or contacts a printer."""
import argparse
import json
import time
import wave
from collections import OrderedDict
from pathlib import Path

import numpy as np

from klippy.audio import Playback, resample
from klippy.audio_probe import TEXT, audit, cached_pipeline
from klippy.models import bundled_pack, verify_pack
from klippy.resampling import SpeechResampler
from klippy.voice import SherpaBackend


def load_tts(root, config):
    import sherpa_onnx as so
    backend = SherpaBackend.__new__(SherpaBackend)
    assert config['tts_kind'] == 'kokoro'
    paths = {key:str(root/value) for key,value in config['tts'].items()}
    backend.tts = so.OfflineTts(so.OfflineTtsConfig(model=so.OfflineTtsModelConfig(
        kokoro=so.OfflineTtsKokoroModelConfig(**paths), num_threads=2)))
    backend.voice_id = config.get('voice_id',0)
    backend.vocabulary = {line.split(' ',1)[0] for line in
                          (root/config['tts']['lexicon']).read_text(encoding='utf-8').splitlines() if line.strip()}
    backend.cache, backend.cache_bytes = OrderedDict(), 0
    return backend


def write_wave(path, data, rate):
    with wave.open(str(path),'wb') as file:
        file.setnchannels(1)
        file.setsampwidth(2)
        file.setframerate(rate)
        file.writeframes((np.clip(data,-1,1)*32767).round().astype('<i2').tobytes())


def run(root, output):
    output.mkdir(parents=True, exist_ok=True)
    manifest = verify_pack(root, require_qualified=True)
    backend = load_tts(root, manifest['speech_config'])
    chunks, arrivals, progress = [], [], []
    started, cpu = time.perf_counter(), time.process_time()
    def chunk(samples, rate):
        chunks.append(np.asarray(samples,dtype=np.float32).copy())
        arrivals.append(time.perf_counter()-started)
    audio = backend.synthesize(TEXT,on_chunk=chunk,on_progress=progress.append)
    generation = time.perf_counter()-started
    cpu = time.process_time()-cpu
    raw = audio.samples
    joined = np.concatenate(chunks)
    linear = resample(raw,audio.sample_rate)
    chunked = np.concatenate([resample(part,audio.sample_rate) for part in chunks])
    playback = Playback()
    playback.enqueue(chunked,playback.generation)
    rendered=[]
    while playback.remaining:
        rendered.append(playback.render(min(160,playback.remaining)))
    rendered=np.concatenate(rendered)
    common=min(len(linear),len(chunked))
    error=chunked[:common]-linear[:common]
    tone=np.sin(2*np.pi*10000*np.arange(24000)/24000).astype(np.float32)
    alias=resample(tone,24000)
    alias_db=20*np.log10(max(float(np.sqrt(np.mean(alias[100:-100]**2))),1e-12)/np.sqrt(.5))
    report={
        'scope':'Synthetic model speech only; no microphone, speaker or printer devices opened',
        'synthetic_text':TEXT, 'source_rate':audio.sample_rate, 'render_rate':16000,
        'source_samples':len(raw),'callback_chunks':[len(part) for part in chunks],
        'chunk_arrival_seconds':arrivals,'generation_seconds':generation,'generation_cpu_seconds':cpu,
        'chunk_progress':progress,
        'original_peak':float(np.max(np.abs(raw))),
        'original_over_range_samples':int(np.count_nonzero(np.abs(raw)>1)),
        'original_finite':bool(np.all(np.isfinite(raw))),
        'callback_concat_equals_original':bool(np.array_equal(joined,raw)),
        'legacy_render_equals_chunked_conversion':bool(np.array_equal(rendered,chunked)),
        'legacy_chunk_sample_count_error':len(chunked)-len(linear),
        'legacy_chunk_vs_batch_rms_error':float(np.sqrt(np.mean(error**2))),
        'legacy_chunk_vs_batch_peak_error':float(np.max(np.abs(error))),
        'legacy_10khz_alias_db':float(alias_db),
        'model_assets':[{k:a[k] for k in ('path','sha256','version')} for a in manifest['assets']
                        if a['path'].endswith('.onnx') and a['path'].startswith('tts/')],
    }
    report['quality']=audit(raw,chunks,audio.sample_rate,arrivals,progress,generation)
    report['quality']['production_cached_pipeline']=cached_pipeline(backend,raw,audio.sample_rate)
    report['quality']['passed']=report['quality']['passed'] and report['quality']['production_cached_pipeline']['passed']
    for name,data,rate in [('kokoro-original',raw,audio.sample_rate),('legacy-chunked',chunked,16000),
                           ('legacy-batch',linear,16000),
                           ('sinc-output',SpeechResampler(audio.sample_rate).push(raw,final=True),16000)]:
        np.save(output/(name+'.npy'),data)
        write_wave(output/(name+'.wav'),data,rate)
    (output/'baseline.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pack',type=Path,default=bundled_pack())
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    run(args.pack,args.output)
