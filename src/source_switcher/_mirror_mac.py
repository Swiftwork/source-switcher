"""macOS display mirroring via CoreGraphics."""

from __future__ import annotations

import ctypes
import ctypes.util
import time

_cg_path = ctypes.util.find_library("CoreGraphics")
if not _cg_path:
    raise RuntimeError("CoreGraphics framework not found")
_cg = ctypes.CDLL(_cg_path)

CGDirectDisplayID = ctypes.c_uint32
CGDisplayCount = ctypes.c_uint32
CGError = ctypes.c_int32

_cg.CGGetOnlineDisplayList.argtypes = [
    CGDisplayCount, ctypes.POINTER(CGDirectDisplayID), ctypes.POINTER(CGDisplayCount),
]
_cg.CGGetOnlineDisplayList.restype = CGError

_cg.CGDisplayIsBuiltin.argtypes = [CGDirectDisplayID]
_cg.CGDisplayIsBuiltin.restype = ctypes.c_int

_cg.CGDisplayIsInMirrorSet.argtypes = [CGDirectDisplayID]
_cg.CGDisplayIsInMirrorSet.restype = ctypes.c_int

_cg.CGDisplayMirrorsDisplay.argtypes = [CGDirectDisplayID]
_cg.CGDisplayMirrorsDisplay.restype = CGDirectDisplayID

_cg.CGBeginDisplayConfiguration.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
_cg.CGBeginDisplayConfiguration.restype = CGError

_cg.CGConfigureDisplayMirrorOfDisplay.argtypes = [
    ctypes.c_void_p, CGDirectDisplayID, CGDirectDisplayID,
]
_cg.CGConfigureDisplayMirrorOfDisplay.restype = CGError

_cg.CGCompleteDisplayConfiguration.argtypes = [ctypes.c_void_p, ctypes.c_int32]
_cg.CGCompleteDisplayConfiguration.restype = CGError

_cg.CGCancelDisplayConfiguration.argtypes = [ctypes.c_void_p]
_cg.CGCancelDisplayConfiguration.restype = CGError

_kCGConfigureForSession = 1
_kCGNullDirectDisplay = 0

_RETRIES = 4
_RETRY_DELAY = 1.0
_VERIFY_DELAY = 0.4


def _get_online_displays() -> list[int]:
    count = CGDisplayCount(0)
    _cg.CGGetOnlineDisplayList(0, None, ctypes.byref(count))
    if count.value == 0:
        return []
    displays = (CGDirectDisplayID * count.value)()
    _cg.CGGetOnlineDisplayList(count.value, displays, ctypes.byref(count))
    return list(displays[: count.value])


def _builtin(displays: list[int]) -> int | None:
    for d in displays:
        if _cg.CGDisplayIsBuiltin(d):
            return d
    return None


def _is_mirroring(builtin: int, displays: list[int]) -> bool:
    for d in displays:
        if d == builtin:
            continue
        if _cg.CGDisplayIsInMirrorSet(d) and _cg.CGDisplayMirrorsDisplay(d) == builtin:
            return True
    return False


def _apply(enable: bool, builtin: int, others: list[int]) -> None:
    config = ctypes.c_void_p()
    err = _cg.CGBeginDisplayConfiguration(ctypes.byref(config))
    if err != 0:
        raise OSError(f"CGBeginDisplayConfiguration failed (error {err})")

    master = builtin if enable else _kCGNullDirectDisplay
    for d in others:
        err = _cg.CGConfigureDisplayMirrorOfDisplay(config, d, master)
        if err != 0:
            _cg.CGCancelDisplayConfiguration(config)
            raise OSError(f"CGConfigureDisplayMirrorOfDisplay failed (error {err})")

    err = _cg.CGCompleteDisplayConfiguration(config, _kCGConfigureForSession)
    if err != 0:
        raise OSError(f"CGCompleteDisplayConfiguration failed (error {err})")


def set_mirror(enable: bool) -> None:
    """Enable or disable mirroring of external displays to the built-in display.

    Retries on transient failures (e.g. when a display is mid-transition after a
    monitor input switch) and verifies the result, since CoreGraphics can accept
    a config but not actually apply it during a transition.
    """
    last_err: Exception | None = None
    for _ in range(_RETRIES):
        displays = _get_online_displays()
        builtin = _builtin(displays)
        if builtin is None:
            last_err = OSError("No built-in display found")
            time.sleep(_RETRY_DELAY)
            continue

        if _is_mirroring(builtin, displays) == enable:
            return

        others = [d for d in displays if d != builtin]
        if not others:
            return

        try:
            _apply(enable, builtin, others)
        except OSError as e:
            last_err = e
            time.sleep(_RETRY_DELAY)
            continue

        time.sleep(_VERIFY_DELAY)
        if _is_mirroring(builtin, _get_online_displays()) == enable:
            return

        last_err = OSError(f"mirror state did not match requested ({'on' if enable else 'off'})")
        time.sleep(_RETRY_DELAY)

    raise last_err or OSError("set_mirror failed")
