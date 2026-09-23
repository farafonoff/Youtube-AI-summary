#!/bin/bash
set -e

PLIST_NAME="com.youtube-watcher.bot"
LAUNCH_AGENT_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$LAUNCH_AGENT_DIR/$PLIST_NAME.plist"

echo "🗑️  Uninstalling YouTube Watcher Bot service..."

# Stop the service
launchctl stop "$PLIST_NAME" 2>/dev/null || true

# Unload the plist
launchctl unload "$PLIST_PATH" 2>/dev/null || true

# Remove the plist
if [ -f "$PLIST_PATH" ]; then
    rm "$PLIST_PATH"
    echo "✅ Removed LaunchAgent plist"
else
    echo "⚠️  Plist not found at $PLIST_PATH (already removed?)"
fi

echo ""
echo "✅ Uninstallation complete!"
echo "💡 To reinstall, run: ./scripts/install.sh"
