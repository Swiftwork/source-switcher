"""macOS DDC/CI via m1ddc (brew install m1ddc)."""

from __future__ import annotations

import shutil
import subprocess


def _find_m1ddc() -> str:
    path = shutil.which("m1ddc")
    if not path:
        raise RuntimeError("m1ddc not found. Install with: brew install m1ddc")
    return path


class MacDDC:
    def __init__(self, display_index: int = 0):
        self._bin = _find_m1ddc()
        # m1ddc uses 1-based display indexing
        self._display = display_index + 1

    def set_source_alt(self, value: int) -> None:
        """Set input source using LG alt protocol (input-alt)."""
        result = subprocess.run(
            [self._bin, "display", str(self._display), "set", "input-alt", str(value)],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            raise OSError(f"m1ddc set input-alt failed: {result.stderr.strip()}")

    def set_source_standard(self, value: int) -> None:
        """Set input source using standard DDC (VCP 0x60)."""
        result = subprocess.run(
            [self._bin, "display", str(self._display), "set", "input", str(value)],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            raise OSError(f"m1ddc set input failed: {result.stderr.strip()}")

    def get_source(self) -> int | None:
        """Read current input source."""
        result = subprocess.run(
            [self._bin, "display", str(self._display), "get", "input"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return None
        try:
            return int(result.stdout.strip())
        except ValueError:
            return None

    def close(self):
        pass
