from types import SimpleNamespace
from unittest.mock import patch

from klippy.voice import VoiceLoop


class Backend:
    def reset_wake(self):
        pass


def test_default_endpoint_change_reopens_both_streams():
    states, opened, initialized = [], [], []
    voice = VoiceLoop(Backend(), lambda value: None, states.append)
    voice.enabled.set()
    class Stream:
        def __init__(self, **kwargs):
            opened.append(kwargs)

        def __enter__(self):
            if len(opened) == 2:
                voice.closed.set()
            return self

        def __exit__(self, *args):
            pass
    api = {"name": "Windows WASAPI", "default_input_device": 1, "default_output_device": 2}
    sd = SimpleNamespace(Stream=Stream, _terminate=lambda: None, _initialize=lambda: initialized.append(True),
                         query_devices=lambda index: {"hostapi": 0},
                         query_hostapis=lambda index=None: api if index is not None else [api],
                         WasapiSettings=lambda **kwargs: kwargs)
    try:
        with patch.dict("sys.modules", {"sounddevice": sd}), patch(
            "klippy.windows_audio.default_endpoint_ids", side_effect=[("mic1", "out1"), ("mic2", "out2"), ("mic2", "out2")]
        ):
            voice._devices()
        assert len(opened) == 2 and len(initialized) == 2
        assert any("changed" in text for text in states)
        assert all(item["device"] == (1, 2) for item in opened)
    finally:
        voice.close()


def test_spoken_notifications_can_play_without_opening_microphone():
    opened = []
    voice = VoiceLoop(Backend(), lambda value: None, lambda text: None)
    voice.speaking.set()
    class Output:
        def __init__(self, **kwargs):
            opened.append(kwargs)

        def __enter__(self):
            voice.closed.set()
            return self

        def __exit__(self, *args):
            pass
    api = {"name": "Windows WASAPI", "default_input_device": -1, "default_output_device": 2}
    sd = SimpleNamespace(OutputStream=Output, _terminate=lambda: None, _initialize=lambda: None,
                         query_devices=lambda index: {"hostapi": 0},
                         query_hostapis=lambda index=None: api if index is not None else [api],
                         WasapiSettings=lambda **kwargs: kwargs)
    try:
        with patch.dict("sys.modules", {"sounddevice": sd}), patch(
            "klippy.windows_audio.default_endpoint_ids", return_value=(None, "speaker")
        ):
            voice._devices()
        assert len(opened) == 1 and opened[0]["device"] == 2
        assert not voice.enabled.is_set()
    finally:
        voice.close()
