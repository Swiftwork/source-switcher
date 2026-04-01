"""
DDC/CI input source switching for LG monitors.

LG 45GX950A uses the "alt" protocol (DDC2AB) for input switching.
m1ddc values: DP1=208, DP2=209, USB-C=210, HDMI1=144, HDMI2=145
"""

from __future__ import annotations

import platform
import sys

# LG alt source values (used by m1ddc input-alt / DDC2AB VCP 0xF4)
SOURCES = {
    "dp1": 208,     # 0xD0
    "dp2": 209,     # 0xD1
    "usbc": 210,    # 0xD2 Seemingly not working
    "hdmi1": 144,   # 0x90
    "hdmi2": 145,   # 0x91
}

if platform.system() == "Darwin":
    from source_switcher._ddc_mac import MacDDC as PlatformDDC
elif platform.system() == "Windows":
    from source_switcher._ddc_win import WindowsDDC as PlatformDDC
else:
    print(f"Unsupported platform: {platform.system()}", file=sys.stderr)
    sys.exit(1)


class Monitor:
    """Wraps platform DDC to switch LG alt input sources."""

    def __init__(self, display_index: int = 0):
        self._ddc = PlatformDDC(display_index)

    def set_source(self, source: str) -> None:
        source = source.lower().replace("-", "").replace("_", "")
        if source not in SOURCES:
            raise ValueError(f"Unknown source '{source}'. Options: {list(SOURCES)}")
        value = SOURCES[source]
        self._ddc.set_source_alt(value)

    def get_source(self) -> int | None:
        return self._ddc.get_source()

    def close(self):
        self._ddc.close()
