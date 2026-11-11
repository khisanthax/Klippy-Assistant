"""Short audio-path smoke test. Never saves audio/text or instantiates printer components."""
import argparse
import json
import time
from pathlib import Path

from klippy.models import verify_pack
from klippy.voice import SherpaBackend, VoiceLoop

parser = argparse.ArgumentParser()
parser.add_argument("pack", type=Path)
parser.add_argument("--output", type=Path, default=Path("local/audio-device-probe.json"))
args = parser.parse_args()
root = args.pack.resolve()
manifest = verify_pack(root, require_qualified=True)
backend = SherpaBackend(root, manifest["speech_config"])
states = []
counts = {"wake_events": 0, "utterance_events": 0}
def on_text(value):
    counts["utterance_events"] += 1  # Deliberately discard text, including any ambient speech.
def on_wake(epoch):
    counts["wake_events"] += 1
voice = VoiceLoop(backend, on_text, states.append, on_wake)
try:
    voice.enabled.set()
    voice.start()
    started = time.monotonic()
    while time.monotonic() - started < 3 and "Microphone ready" not in states:
        time.sleep(.05)
    if "Microphone ready" in states:
        voice.say("Klippy is running locally. This is a short offline audio test.")
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and "Speech finished" not in states:
            time.sleep(.1)
finally:
    voice.close()
report = {"scope": "Windows default audio open/capture/render smoke only; no accuracy claim",
          "microphone_stream_opened": "Microphone ready" in states,
          "tts_completed": "Speech finished" in states,
          "audio_frames_processed": voice.echo.frames,
          "queue_depth_at_shutdown": voice.audio.qsize(), "events": counts,
          "states": states, "recordings_saved": False, "transcripts_saved": False,
          "device_error": voice.last_device_error,
          "printer_connections": 0}
args.output.write_text(json.dumps(report, indent=2), encoding="utf-8", newline="\n")
print(json.dumps(report, indent=2))
