"""Cross-platform USB device connection monitoring via polling."""

from __future__ import annotations

import platform
import re
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class USBDevice:
    vendor_id: str
    product_id: str
    name: str = ""

    @property
    def vid_pid(self) -> str:
        return f"{self.vendor_id}:{self.product_id}"


def _list_usb_mac() -> list[USBDevice]:
    """Parse ioreg for USB devices with vendor/product IDs and names."""
    try:
        out = subprocess.check_output(
            ["/usr/sbin/ioreg", "-p", "IOUSB", "-l", "-w0"],
            text=True, timeout=5,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return []

    devices: list[USBDevice] = []
    seen: set[str] = set()
    vid = pid = None
    name = ""

    def flush() -> None:
        if vid is None or pid is None:
            return
        key = f"{vid:04x}:{pid:04x}"
        if key in seen:
            return
        seen.add(key)
        devices.append(USBDevice(f"{vid:04x}", f"{pid:04x}", name))

    for line in out.splitlines():
        # "+-o <name>" marks a new device entry — flush before resetting state
        # so we never associate a vid/pid pair with the wrong device.
        if "+-o " in line:
            flush()
            vid = pid = None
            name = ""
            continue

        m = re.search(r'"idVendor"\s*=\s*(\d+)', line)
        if m:
            vid = int(m.group(1))
            continue
        m = re.search(r'"idProduct"\s*=\s*(\d+)', line)
        if m:
            pid = int(m.group(1))
            continue
        m = re.search(r'"USB Product Name"\s*=\s*"([^"]*)"', line)
        if m:
            name = m.group(1)

    flush()
    return devices


def _list_usb_win() -> list[USBDevice]:
    """Query PowerShell for USB devices with FriendlyName + VID/PID."""
    try:
        out = subprocess.check_output(
            [
                "powershell", "-NoProfile", "-Command",
                "Get-PnpDevice -Class USB -Status OK | "
                "Select-Object FriendlyName, InstanceId | ConvertTo-Csv -NoTypeInformation"
            ],
            text=True, timeout=10,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return []

    devices: list[USBDevice] = []
    seen: set[str] = set()
    for line in out.splitlines()[1:]:
        m = re.search(r'"([^"]*)","([^"]*)"', line)
        if not m:
            continue
        name, instance = m.group(1), m.group(2)
        vp = re.search(r"VID_([0-9A-Fa-f]{4})&PID_([0-9A-Fa-f]{4})", instance)
        if not vp:
            continue
        key = f"{vp.group(1).lower()}:{vp.group(2).lower()}"
        if key in seen:
            continue
        seen.add(key)
        devices.append(USBDevice(vp.group(1).lower(), vp.group(2).lower(), name))
    return devices


def list_usb_detailed() -> list[USBDevice]:
    """List currently connected USB devices with names."""
    if platform.system() == "Darwin":
        return _list_usb_mac()
    if platform.system() == "Windows":
        return _list_usb_win()
    return []


def _list_vid_pids() -> set[str]:
    return {d.vid_pid for d in list_usb_detailed()}


class USBWatcher:
    """Polls for USB device connect/disconnect events."""

    def __init__(self, poll_interval: float = 2.0):
        self.poll_interval = poll_interval
        self._prev: set[str] = _list_vid_pids()

    def poll(self) -> tuple[set[str], set[str]]:
        """Returns (connected, disconnected) device VID:PID sets since last poll."""
        current = _list_vid_pids()
        connected = current - self._prev
        disconnected = self._prev - current
        self._prev = current
        return connected, disconnected

    def current_devices(self) -> set[str]:
        self._prev = _list_vid_pids()
        return set(self._prev)
