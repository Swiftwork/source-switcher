"""Windows DDC/CI via Dxva2.dll.

Uses SetVCPFeature with VCP 0xF4 for LG alt input switching.
If standard Dxva2 doesn't work for DDC2AB on your setup, consider
using ControlMyMonitor (NirSoft) or Twinkle Tray as alternatives.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wt
from ctypes import Structure, POINTER, byref, windll

VCP_INPUT_ALT = 0xF4


class PHYSICAL_MONITOR(Structure):
    _fields_ = [
        ("hPhysicalMonitor", wt.HANDLE),
        ("szPhysicalMonitorDescription", wt.WCHAR * 128),
    ]


_dxva2 = windll.LoadLibrary("Dxva2.dll")
_user32 = windll.user32

MONITORENUMPROC = ctypes.WINFUNCTYPE(
    wt.BOOL, wt.HMONITOR, wt.HDC, POINTER(wt.RECT), wt.LPARAM
)
_user32.EnumDisplayMonitors.argtypes = [wt.HDC, POINTER(wt.RECT), MONITORENUMPROC, wt.LPARAM]
_user32.EnumDisplayMonitors.restype = wt.BOOL

_dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR.argtypes = [wt.HMONITOR, POINTER(wt.DWORD)]
_dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR.restype = wt.BOOL
_dxva2.GetPhysicalMonitorsFromHMONITOR.argtypes = [wt.HMONITOR, wt.DWORD, POINTER(PHYSICAL_MONITOR)]
_dxva2.GetPhysicalMonitorsFromHMONITOR.restype = wt.BOOL
_dxva2.SetVCPFeature.argtypes = [wt.HANDLE, wt.BYTE, wt.DWORD]
_dxva2.SetVCPFeature.restype = wt.BOOL
_dxva2.GetVCPFeatureAndVCPFeatureReply.argtypes = [
    wt.HANDLE, wt.BYTE, POINTER(wt.DWORD), POINTER(wt.DWORD), POINTER(wt.DWORD)
]
_dxva2.GetVCPFeatureAndVCPFeatureReply.restype = wt.BOOL
_dxva2.DestroyPhysicalMonitor.argtypes = [wt.HANDLE]
_dxva2.DestroyPhysicalMonitor.restype = wt.BOOL


def _get_monitors() -> list[wt.HMONITOR]:
    monitors: list[wt.HMONITOR] = []

    @MONITORENUMPROC
    def callback(hmon, hdc, rect, data):
        monitors.append(hmon)
        return True

    _user32.EnumDisplayMonitors(None, None, callback, 0)
    return monitors


class WindowsDDC:
    def __init__(self, display_index: int = 0):
        monitors = _get_monitors()
        if not monitors:
            raise RuntimeError("No monitors found")
        if display_index >= len(monitors):
            raise RuntimeError(f"Display index {display_index} out of range ({len(monitors)} found)")
        count = wt.DWORD()
        if not _dxva2.GetNumberOfPhysicalMonitorsFromHMONITOR(monitors[display_index], byref(count)):
            raise OSError("GetNumberOfPhysicalMonitorsFromHMONITOR failed")
        arr = (PHYSICAL_MONITOR * count.value)()
        if not _dxva2.GetPhysicalMonitorsFromHMONITOR(monitors[display_index], count, arr):
            raise OSError("GetPhysicalMonitorsFromHMONITOR failed")
        self._handle = arr[0].hPhysicalMonitor

    def set_source_alt(self, value: int) -> None:
        if not _dxva2.SetVCPFeature(self._handle, VCP_INPUT_ALT, value):
            raise OSError(f"SetVCPFeature(0x{VCP_INPUT_ALT:02x}, {value}) failed")

    def set_source_standard(self, value: int) -> None:
        if not _dxva2.SetVCPFeature(self._handle, 0x60, value):
            raise OSError(f"SetVCPFeature(0x60, {value}) failed")

    def get_source(self) -> int | None:
        vcp_type = wt.DWORD()
        current = wt.DWORD()
        maximum = wt.DWORD()
        if not _dxva2.GetVCPFeatureAndVCPFeatureReply(
            self._handle, 0x60, byref(vcp_type), byref(current), byref(maximum)
        ):
            return None
        return current.value

    def close(self):
        if self._handle:
            _dxva2.DestroyPhysicalMonitor(self._handle)
            self._handle = None
