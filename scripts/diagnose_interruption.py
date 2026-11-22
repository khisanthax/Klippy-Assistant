"""Device-free timing experiment for the preview.3 synthetic two-speaker interruption."""
import argparse
import hashlib
import json
from collections import deque
from pathlib import Path
from unittest.mock import patch

import numpy as np

from klippy.audio import FRAME, RATE, resample
from klippy.models import verify_pack
from klippy.offline_probe import deny_external_network
from klippy.speech_text import normalize_for_speech
from klippy.voice import SherpaBackend, VoiceLoop


def fingerprint(samples):
    return hashlib.sha256(np.asarray(samples, dtype="<f4").tobytes()).hexdigest()


def replay(backend, speaker, user, delay_frames):
    """Complete queued ASR work on a specified capture frame using the real decoder."""
    requests, wakes, observations = [], [], []
    pending = deque()
    frame = 0

    def now():
        return frame * FRAME / RATE

    def on_wake(epoch):
        wakes.append({"frame": frame, "epoch": epoch, "remaining": voice.playback.remaining})

    backend.reset_wake()
    voice = VoiceLoop(backend, requests.append, lambda state: None, on_wake, clock=now)
    voice.enabled.set()
    decode = backend.transcribe

    def observed_decode(samples):
        rolling = voice.probe_pending.is_set()
        text = decode(samples)
        row = {"stage": "rolling" if rolling else "utterance", "frame": frame,
               "pcm_sha256": fingerprint(samples), "samples": len(samples), "text": text}
        if not rolling:
            # Diagnostic control only. Only the original decode reaches VoiceLoop.
            row["same_pcm_redecode"] = decode(samples.copy())
        observations.append(row)
        return text

    start = 3 * RATE
    length = max(len(speaker), start + len(user)) + 2 * RATE
    reference = np.pad(speaker, (0, length - len(speaker)))
    history = np.zeros_like(reference)
    voice.playback.enqueue(reference, voice.epoch)

    def schedule(work):
        pending.append((frame + delay_frames, work))

    try:
        with patch.object(voice.asr_pool, "submit", schedule), patch.object(backend, "transcribe", observed_decode):
            for i in range(0, length - FRAME, FRAME):
                frame += 1
                far = voice.playback.render(FRAME)
                history[i:i + FRAME] = far
                near = np.zeros_like(far)
                for delay, gain in ((800, .6), (1120, .1)):
                    if i >= delay:
                        near += gain * history[i - delay:i - delay + FRAME]
                left, right = max(i, start), min(i + FRAME, start + len(user))
                if right > left:
                    near[left - i:right - i] += .8 * user[left - start:right - start]
                voice.process_frame(near, far, now(), output_active=bool(voice.playback.remaining))
                while pending and pending[0][0] <= frame:
                    pending.popleft()[1]()
            while pending:
                frame, work = pending.popleft()
                work()
        return {"worker_delay_frames": delay_frames, "wakes": wakes, "asr": observations,
                "delivered": [request.text for request in requests],
                "prefix_rejected": voice.wake_diagnostics()["prefix_rejected"]}
    finally:
        voice.close()


def run(pack):
    deny_external_network()
    manifest = verify_pack(pack, require_qualified=True)
    backend = SherpaBackend(pack, manifest["speech_config"])

    def synthesize(text, sid):
        result = backend.tts.generate(normalize_for_speech(text, backend.vocabulary), sid=sid, speed=1.)
        return resample(result.samples, result.sample_rate)

    # Within a set both source signals are held fixed. Between sets regenerate both.
    report = {"model_manifest_sha256": hashlib.sha256((pack / "manifest.json").read_bytes()).hexdigest(),
              "sample_rate": RATE, "frame_samples": FRAME, "stimuli": []}
    for _ in range(2):
        speaker = synthesize("The test printer is currently printing. The job is sixty three percent complete. "
                             "Please ask if you need more details.", 3)
        user = synthesize("Klippy stop talking", 0)
        report["stimuli"].append({"speaker_sha256": fingerprint(speaker), "user_sha256": fingerprint(user),
                                  "runs": [replay(backend, speaker, user, n) for n in (12, 14, 16, 18, 20, 12)]})
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pack", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(json.dumps(run(args.pack), indent=2) + "\n", encoding="utf-8")
