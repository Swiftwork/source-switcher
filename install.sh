#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.swiftwork.source-switcher"
PLIST_SRC="$SCRIPT_DIR/$PLIST_NAME.plist"

if [ "$(uname)" != "Darwin" ]; then
    echo "This installer is for macOS. On Windows, use install.ps1"
    exit 1
fi

if [ "$(id -u)" -eq 0 ]; then
    echo "Do not run with sudo. LaunchAgents are per-user services."
    exit 1
fi

# Check m1ddc
if ! command -v m1ddc &>/dev/null; then
    echo "m1ddc not found. Installing via Homebrew..."
    brew install m1ddc
fi

# Prompt for config
echo "Detecting connected USB devices..."
USB_LIST=$(PYTHONPATH="$SCRIPT_DIR/src" python3 -c '
from source_switcher.usb_watch import list_usb_detailed
for d in sorted(list_usb_detailed(), key=lambda x: x.vid_pid):
    name = d.name or "(unknown)"
    print(d.vid_pid + "\t" + name)
')

if [ -n "$USB_LIST" ]; then
    echo ""
    echo "Connected USB devices:"
    i=1
    declare -a USB_IDS
    while IFS=$'\t' read -r vid_pid name; do
        printf "  %2d) %s  %s\n" "$i" "$vid_pid" "$name"
        USB_IDS[$i]="$vid_pid"
        i=$((i + 1))
    done <<< "$USB_LIST"
    echo ""
    read -p "Pick a number, or enter VID:PID manually: " USB_CHOICE
    if [[ "$USB_CHOICE" =~ ^[0-9]+$ ]] && [ -n "${USB_IDS[$USB_CHOICE]}" ]; then
        USB_ID="${USB_IDS[$USB_CHOICE]}"
        echo "Selected: $USB_ID"
    else
        USB_ID="$USB_CHOICE"
    fi
else
    read -p "USB VID:PID to watch: " USB_ID
fi
read -p "Source on connect [dp2]: " ON_CONNECT
ON_CONNECT="${ON_CONNECT:-dp2}"
read -p "Source on disconnect [dp1]: " ON_DISCONNECT
ON_DISCONNECT="${ON_DISCONNECT:-dp1}"
read -p "Display index, 0-based [1]: " DISPLAY_IDX
DISPLAY_IDX="${DISPLAY_IDX:-1}"
read -p "Mirror display on disconnect? [y/N]: " MIRROR_OPT
MIRROR_OPT="${MIRROR_OPT:-n}"

# Remove any existing service
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"
GUI_DOMAIN="gui/$(id -u)"

echo "Stopping existing service (if any)..."
launchctl bootout "$GUI_DOMAIN/$PLIST_NAME" 2>/dev/null || true
# Belt-and-suspenders: bootout sometimes leaves the process running.
pkill -f "source_switcher.*watch" 2>/dev/null || true
rm -f "$PLIST_DEST"

mkdir -p "$HOME/Library/LaunchAgents"

PYTHON3="$(command -v python3)"

MIRROR_ARG=""
if [[ "$MIRROR_OPT" =~ ^[Yy] ]]; then
    MIRROR_ARG="
        <string>--mirror-on-disconnect</string>"
fi

cat > "$PLIST_DEST" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_NAME</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON3</string>
        <string>-u</string>
        <string>-m</string>
        <string>source_switcher</string>
        <string>--display</string>
        <string>$DISPLAY_IDX</string>
        <string>watch</string>
        <string>--usb</string>
        <string>$USB_ID</string>
        <string>--on-connect</string>
        <string>$ON_CONNECT</string>
        <string>--on-disconnect</string>
        <string>$ON_DISCONNECT</string>$MIRROR_ARG
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>$SCRIPT_DIR/src</string>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/sbin:/usr/bin:/bin</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/source-switcher.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/source-switcher.log</string>
</dict>
</plist>
EOF

launchctl bootstrap "$GUI_DOMAIN" "$PLIST_DEST"

echo ""
echo "Installed and started."
echo "  Logs: /tmp/source-switcher.log"
echo "  Stop: launchctl bootout $GUI_DOMAIN/$PLIST_NAME"
echo "  Start: launchctl bootstrap $GUI_DOMAIN $PLIST_DEST"
