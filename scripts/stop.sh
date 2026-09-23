#!/bin/bash
set -e

PLIST_NAME="com.youtube-watcher.bot"
LAUNCH_AGENT_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$LAUNCH_AGENT_DIR/$PLIST_NAME.plist"

echo "🛑 Stopping YouTube Watcher Bot..."

# Stop the service
launchctl stop "$PLIST_NAME" 2>/dev/null || true

# Unload the plist
launchctl unload "$PLIST_PATH" 2>/dev/null || true

echo "✅ Bot stopped."
echo "💡 To start again: ./scripts/start.sh"
