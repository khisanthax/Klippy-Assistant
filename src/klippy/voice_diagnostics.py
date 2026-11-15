"""Explicit, credential-free voice events; presentation never authorizes input."""
import time
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class Definition:
    code: str
    stage: str
    reason: str
    attention: bool = False


DEFINITIONS = {
    "wake_candidate": Definition("wake_candidate", "wake", "Checking the wake phrase."),
    "wake_verified": Definition("wake_verified", "wake", "Wake phrase recognized."),
    "wake_prefix_rejected": Definition("wake_prefix_rejected", "wake_verification", "Wake phrase wasn't recognized. Please say Klippy, then pause.", True),
    "wake_verification_unavailable": Definition("wake_verification_unavailable", "wake_verification", "Wake verification failed. No request was accepted.", True),
    "asr_unavailable": Definition("asr_unavailable", "asr", "Speech recognition failed. No request was sent.", True),
    "asr_empty": Definition("asr_empty", "asr", "No speech was recognized. Please repeat your request.", True),
    "audio_discontinuity": Definition("audio_discontinuity", "capture", "Microphone audio was interrupted. Please wake Klippy again.", True),
    "audio_processing_unavailable": Definition("audio_processing_unavailable", "capture", "Microphone audio processing failed. No request was sent.", True),
    "audio_device_unavailable": Definition("audio_device_unavailable", "device", "Microphone or speaker connection interrupted. Klippy is reconnecting.", True),
    "audio_device_changed": Definition("audio_device_changed", "device", "Audio device changed; reconnecting."),
    "microphone_ready": Definition("microphone_ready", "device", "Microphone ready."),
    "speech_queue_full": Definition("speech_queue_full", "asr_queue", "Speech recognition is busy. Please wake Klippy and repeat.", True),
    "playback_delivery_failed": Definition("playback_delivery_failed", "playback", "Speech playback failed. The reply is still available in Klippy.", True),
    "tts_unavailable": Definition("tts_unavailable", "tts", "Speech playback failed. The reply is still available in Klippy.", True),
    "processing_timeout": Definition("processing_timeout", "conversation", "The response took too long. Open Klippy for details.", True),
    "application_error": Definition("application_error", "application", "Klippy couldn't finish the request. Open Klippy for details.", True),
    "printer_alert": Definition("printer_alert", "monitoring", "A printer alert needs attention. Open Klippy for details.", True),
}

# Exact legacy messages only; an arbitrary word such as 'full' is never an error classifier.
MESSAGES = {
    "Checking wake word": "wake_candidate",
    "Listening": "wake_verified",
    "Microphone ready": "microphone_ready",
    "Wake transcript unclear": "wake_prefix_rejected",
    "Wake transcript unclear; please repeat Klippy and the request": "wake_prefix_rejected",
    "Wake verification unavailable; keyword detector remains active": "wake_verification_unavailable",
    "Speech recognition unavailable; no request sent": "asr_unavailable",
    "Audio discontinuity": "audio_discontinuity",
    "Audio discontinuity; please wake Klippy and repeat": "audio_discontinuity",
    "Audio processing unavailable; no request sent": "audio_processing_unavailable",
    "Microphone or speaker unavailable; retrying safely": "audio_device_unavailable",
    "Default audio device changed; reconnecting": "audio_device_changed",
    "Speech queue full; please wake Klippy and repeat": "speech_queue_full",
    "Speaker or speech model unavailable; text remains accessible": "tts_unavailable",
}


def definition(event):
    return DEFINITIONS.get(getattr(event, "code", None) or MESSAGES.get(str(event)))


def snapshot(event, *, code=None):
    item = DEFINITIONS.get(code) if code else definition(event)
    if item is None:
        return None
    return {"diagnostic": item.code, "voice_stage": item.stage, "reason": item.reason,
            "diagnostic_timestamp": getattr(event, "timestamp", time.time()),
            "event_id": getattr(event, "event_id", None) or uuid.uuid4().hex,
            "event_epoch": getattr(event, "epoch", None),
            "wake_counts": dict(getattr(event, "wake_counts", {})),
            "session_id": getattr(event, "session_id", None),
            "session_state": "active" if getattr(event, "session_id", None) else "not_opened",
            "attempt_id": getattr(event, "attempt_id", None)}
