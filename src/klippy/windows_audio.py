"""Read Windows multimedia default endpoint IDs without opening capture/playback devices."""
import ctypes
import os
import uuid


def default_endpoint_ids(*, require_input=True):
    if os.name != "nt":
        import sounddevice as sd
        return tuple(sd.default.device)
    # PortAudio may already have initialized this thread as STA. WinDLL lets us
    # handle RPC_E_CHANGED_MODE without OleDLL raising before HRESULT inspection.
    ole = ctypes.WinDLL("ole32")
    ole.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    ole.CoInitializeEx.restype = ctypes.c_long
    initialized = ole.CoInitializeEx(None, 0)
    ole.CoCreateInstance.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong,
                                    ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    ole.CoCreateInstance.restype = ctypes.c_long
    ole.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    enum = ctypes.c_void_p()
    clsid = (ctypes.c_ubyte * 16).from_buffer_copy(uuid.UUID("BCDE0395-E52F-467C-8E3D-C4579291692E").bytes_le)
    iid = (ctypes.c_ubyte * 16).from_buffer_copy(uuid.UUID("A95664D2-9614-4F35-A746-DE8DB63617E6").bytes_le)
    def method(pointer, index, result, *args):
        table = ctypes.cast(pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        return ctypes.WINFUNCTYPE(result, ctypes.c_void_p, *args)(table[index])
    try:
        if ole.CoCreateInstance(ctypes.byref(clsid), None, 1, ctypes.byref(iid), ctypes.byref(enum)) != 0:
            raise OSError("Windows audio endpoint enumeration unavailable")
        result = []
        get_default = method(enum, 4, ctypes.c_long, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))
        for flow in (1, 0):  # Capture, render; eMultimedia role.
            device = ctypes.c_void_p()
            if get_default(enum, flow, 1, ctypes.byref(device)) != 0:
                if flow == 1 and not require_input:
                    result.append(None)
                    continue
                raise OSError("No default Windows audio endpoint")
            value = ctypes.c_void_p()
            try:
                get_id = method(device, 5, ctypes.c_long, ctypes.POINTER(ctypes.c_void_p))
                if get_id(device, ctypes.byref(value)) != 0:
                    raise OSError("Windows audio endpoint identity unavailable")
                result.append(ctypes.wstring_at(value))
            finally:
                if value:
                    ole.CoTaskMemFree(value)
                method(device, 2, ctypes.c_ulong)(device)
        return tuple(result)
    finally:
        if enum:
            method(enum, 2, ctypes.c_ulong)(enum)
        if initialized in (0, 1):
            ole.CoUninitialize()
