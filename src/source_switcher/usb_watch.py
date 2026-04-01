"""Cross-platform USB device connection monitoring via polling."""

from __future__ import annotations

import platform
import re
import subprocess
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class USBDevice:
    vendor_id: str
    product_id: str
    name: str = ""

    @property
    def vid_pid(self) -> str:
        return f"{self.vendor_id}:{self.product_id}"


def _list_usb_mac() -> set[str]:
    """Return set of vendor:product IDs from ioreg or system_profiler."""
    devices = set()

    # Try ioreg first (faster)
    try:
        out = subprocess.check_output(
            ["/usr/sbin/ioreg", "-p", "IOUSB", "-l", "-w0"],
            text=True, timeout=5,
        )
        vid = pid = None
        for line in out.splitlines():
            m = re.search(r'"idVendor"\s*=\s*(\d+)', line)
            if m:
                vid = int(m.group(1))
            m = re.search(r'"idProduct"\s*=\s*(\d+)', line)
            if m:
                pid = int(m.group(1))
            if vid is not None and pid is not None:
                devices.add(f"{vid:04x}:{pid:04x}")
                vid = pid = None
        if devices:
            return devices
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    # Fallback: system_profiler (slower but more reliable)
    try:
        out = subprocess.check_output(
            ["system_profiler", "SPUSBDataType"],
            text=True, timeout=15,
        )
        vid = pid = None
        for line in out.splitlines():
            m = re.search(r"Vendor ID:\s*0x([0-9a-fA-F]{4})", line)
            if m:
                vid = m.group(1).lower()
            m = re.search(r"Product ID:\s*0x([0-9a-fA-F]{4})", line)
            if m:
                pid = m.group(1).lower()
            if vid and pid:
                devices.add(f"{vid}:{pid}")
                vid = pid = None
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    return devices


def _list_usb_win() -> set[str]:
    """Return set of vendor:product IDs from PowerShell."""
    try:
        out = subprocess.check_output(
            [
                "powershell", "-NoProfile", "-Command",
                "Get-PnpDevice -Class USB -Status OK | "
                "Select-Object -ExpandProperty InstanceId"
            ],
            text=True, timeout=10,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return set()

    devices = set()
    for line in out.splitlines():
        m = re.search(r"VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})", line)
        if m:
            devices.add(f"{m.group(1).lower()}:{m.group(2).lower()}")
    return devices


_list_usb = _list_usb_mac if platform.system() == "Darwin" else _list_usb_win


class USBWatcher:
    """Polls for USB device connect/disconnect events."""

    def __init__(self, poll_interval: float = 2.0):
        self.poll_interval = poll_interval
        self._prev: set[str] = _list_usb()

    def poll(self) -> tuple[set[str], set[str]]:
        """Returns (connected, disconnected) device VID:PID sets since last poll."""
        current = _list_usb()
        connected = current - self._prev
        disconnected = self._prev - current
        self._prev = current
        return connected, disconnected

    def current_devices(self) -> set[str]:
        self._prev = _list_usb()
        return set(self._prev)
