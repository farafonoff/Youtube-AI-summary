#!/bin/bash
set -e

PLIST_NAME="com.youtube-watcher.bot"
LAUNCH_AGENT_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$LAUNCH_AGENT_DIR/$PLIST_NAME.plist"

echo "🚀 Starting YouTube Watcher Bot..."

# Load plist if not already loaded
launchctl load "$PLIST_PATH" 2>/dev/null || true

# Start the service
launchctl start "$PLIST_NAME"

echo "✅ Bot started successfully."
echo "💡 Check status with: ./scripts/status.sh"
echo "💡 View logs with: tail -f logs/bot.log"
