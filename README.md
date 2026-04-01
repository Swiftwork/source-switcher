# source-switcher

Auto-switch LG 45GX950A monitor input source when a USB device connects or disconnects. Uses the LG alternate DDC protocol (DDC2AB, VCP `0xF4`) since standard DDC input switching doesn't work on this monitor.

## Requirements

- Python 3.10+
- **macOS**: [m1ddc](https://github.com/waydabber/m1ddc) (Apple Silicon) — `brew install m1ddc`
- **Windows**: No extra dependencies (uses built-in Dxva2.dll)

## Usage

```bash
# List USB devices to find the VID:PID to watch
PYTHONPATH=src python3 -m source_switcher list-usb

# Switch input manually
PYTHONPATH=src python3 -m source_switcher switch dp1
PYTHONPATH=src python3 -m source_switcher switch dp2

# Watch for USB device and auto-switch
PYTHONPATH=src python3 -m source_switcher watch \
  --usb 05e3:0626 --on-connect dp2 --on-disconnect dp1
```

### Sources

| Name    | Value | Description           |
| ------- | ----- | --------------------- |
| `dp1`   | 208   | DisplayPort 1         |
| `dp2`   | 209   | DisplayPort 2         |
| `usbc`  | 210   | USB-C (try dp2 first) |
| `hdmi1` | 144   | HDMI 1                |
| `hdmi2` | 145   | HDMI 2                |

### Options

| Flag          | Default | Description                  |
| ------------- | ------- | ---------------------------- |
| `--display N` | `1`     | Display index, 0-based       |
| `--interval`  | `2.0`   | USB poll interval in seconds |

## Run at startup

### macOS

```bash
./install.sh
```

Prompts for USB VID:PID, sources, and display index, then installs a LaunchAgent that starts on login and auto-restarts on crash.

```bash
# Logs
tail -f /tmp/source-switcher.log

# Stop
launchctl bootout gui/$(id -u)/com.swiftwork.source-switcher

# Start
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.swiftwork.source-switcher.plist
```

### Windows

```powershell
.\install.ps1
```

Installs a startup script that runs in the background on login.

## How it works

1. Polls for USB device connect/disconnect events via `ioreg` (macOS) or PowerShell (Windows)
2. When the watched USB VID:PID appears or disappears, sends a DDC2AB input switch command to the monitor
3. On macOS, delegates to `m1ddc` which handles the LG alternate addressing (`input-alt`)
4. On Windows, uses `SetVCPFeature` via `Dxva2.dll` with VCP code `0xF4`

## Notes

- The LG 45GX950A does not reliably support DDC reads, so `status` may not report the current source
- Standard DDC input switching (VCP `0x60`) is ignored by this monitor — the alt protocol is required
- The `usbc` source (210/0xD2) may not work on all configurations
