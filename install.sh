#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST_NAME="com.swiftwork.source-switcher"
PLIST_SRC="$SCRIPT_DIR/$PLIST_NAME.plist"

if [ "$(uname)" != "Darwin" ]; then
    echo "This installer is for macOS. On Windows, use install.ps1"
    exit 1
fi

# Check m1ddc
if ! command -v m1ddc &>/dev/null; then
    echo "m1ddc not found. Installing via Homebrew..."
    brew install m1ddc
fi

# Prompt for config
read -p "USB VID:PID to watch (run 'python3 -m source_switcher list-usb' to find it): " USB_ID
read -p "Source on connect [dp2]: " ON_CONNECT
ON_CONNECT="${ON_CONNECT:-dp2}"
read -p "Source on disconnect [dp1]: " ON_DISCONNECT
ON_DISCONNECT="${ON_DISCONNECT:-dp1}"
read -p "Display index, 0-based [1]: " DISPLAY_IDX
DISPLAY_IDX="${DISPLAY_IDX:-1}"

# Generate plist
mkdir -p "$HOME/Library/LaunchAgents"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME.plist"

# Unload if already running
launchctl bootout "gui/$(id -u)/$PLIST_NAME" 2>/dev/null || true

PYTHON3="$(command -v python3)"

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
        <string>$ON_DISCONNECT</string>
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

launchctl bootstrap "gui/$(id -u)" "$PLIST_DEST"

echo ""
echo "Installed and started."
echo "  Logs: /tmp/source-switcher.log"
echo "  Stop: launchctl bootout gui/$(id -u)/$PLIST_NAME"
echo "  Start: launchctl bootstrap gui/$(id -u) $PLIST_DEST"
