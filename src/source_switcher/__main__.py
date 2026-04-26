"""
source-switcher: Auto-switch LG 45GX950A input source on USB connect/disconnect.

Usage:
  source-switcher watch --usb VID:PID --on-connect usbc --on-disconnect dp
  source-switcher switch <source>
  source-switcher list-usb
  source-switcher status
"""

from __future__ import annotations

import argparse
import platform
import signal
import sys
import time

from source_switcher.ddc import Monitor, SOURCES

_MIRROR_SETTLE_SECONDS = 2.0


def cmd_switch(args):
    mon = Monitor(display_index=args.display)
    try:
        mon.set_source(args.source)
        print(f"Switched to {args.source}")
    finally:
        mon.close()


def cmd_status(args):
    mon = Monitor(display_index=args.display)
    try:
        val = mon.get_source()
        if val is None or val < 0:
            print("Could not read current source (LG monitors may not support DDC reads)")
            return
        name = next((k for k, v in SOURCES.items() if v == val), str(val))
        print(f"Current source: {name} ({val})")
    finally:
        mon.close()


def cmd_list_usb(args):
    from source_switcher.usb_watch import list_usb_detailed
    devices = list_usb_detailed()
    if not devices:
        print("No USB devices found")
        return
    print("Connected USB devices:")
    for d in sorted(devices, key=lambda x: x.vid_pid):
        print(f"  {d.vid_pid}  {d.name or '(unknown)'}")


def _handle_event(mon: Monitor, vid_pid: str, action: str, source: str,
                  mirror_target: bool | None) -> None:
    """Switch the monitor source and optionally toggle display mirroring."""
    print(f"USB {vid_pid} {action} -> switching to {source}")
    try:
        mon.set_source(source)
    except OSError as e:
        print(f"  Switch failed: {e}", file=sys.stderr)

    if mirror_target is None:
        return

    # Let the monitor's HPD transition settle before reconfiguring displays.
    time.sleep(_MIRROR_SETTLE_SECONDS)
    try:
        from source_switcher._mirror_mac import set_mirror
        set_mirror(mirror_target)
        state = "enabled" if mirror_target else "disabled (extended)"
        print(f"  Display mirroring {state}")
    except OSError as e:
        print(f"  Mirror toggle failed: {e}", file=sys.stderr)


def cmd_watch(args):
    from source_switcher.usb_watch import USBWatcher

    if args.mirror_on_disconnect and platform.system() != "Darwin":
        print("--mirror-on-disconnect is only supported on macOS", file=sys.stderr)
        sys.exit(1)

    vid_pid = args.usb.lower()
    on_connect = args.on_connect
    on_disconnect = args.on_disconnect
    interval = args.interval
    mirror = args.mirror_on_disconnect

    mon = Monitor(display_index=args.display)
    watcher = USBWatcher(poll_interval=interval)

    # Log initial state without switching (avoids a screen blank on startup)
    usb_present = vid_pid in watcher.current_devices()
    if usb_present:
        print(f"USB {vid_pid} already connected (assuming {on_connect})")
    else:
        print(f"USB {vid_pid} not connected (assuming {on_disconnect})")

    if mirror:
        print("Display mirroring: ON on disconnect, OFF on connect")

    print(f"Watching for {vid_pid} (poll every {interval}s)... Ctrl+C to stop")

    running = True
    def _stop(*_):
        nonlocal running
        running = False
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    try:
        while running:
            time.sleep(interval)
            connected, disconnected = watcher.poll()
            if vid_pid in connected:
                _handle_event(mon, vid_pid, "connected", on_connect,
                              False if mirror else None)
            elif vid_pid in disconnected:
                _handle_event(mon, vid_pid, "disconnected", on_disconnect,
                              True if mirror else None)
    finally:
        mon.close()
        print("\nStopped.")


def main():
    p = argparse.ArgumentParser(
        prog="source-switcher",
        description="Auto-switch LG 45GX950A input on USB connect/disconnect",
    )
    p.add_argument("--display", type=int, default=1, help="Display index, 0-based (default: 1)")

    sub = p.add_subparsers(dest="command", required=True)

    sw = sub.add_parser("switch", help="Switch input source")
    sw.add_argument("source", choices=list(SOURCES), help="Input source name")

    sub.add_parser("status", help="Read current input source")
    sub.add_parser("list-usb", help="List connected USB devices")

    w = sub.add_parser("watch", help="Watch for USB and auto-switch")
    w.add_argument("--usb", required=True, help="USB VID:PID to watch (e.g. 05e3:0626)")
    w.add_argument("--on-connect", required=True, choices=list(SOURCES), help="Source when USB connected")
    w.add_argument("--on-disconnect", required=True, choices=list(SOURCES), help="Source when USB disconnected")
    w.add_argument("--interval", type=float, default=2.0, help="Poll interval in seconds (default: 2)")
    w.add_argument("--mirror-on-disconnect", action="store_true",
                   help="Enable display mirroring on disconnect, disable on connect (macOS only)")

    args = p.parse_args()
    {"switch": cmd_switch, "status": cmd_status, "list-usb": cmd_list_usb, "watch": cmd_watch}[args.command](args)


if __name__ == "__main__":
    main()
