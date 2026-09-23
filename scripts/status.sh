#!/bin/bash

PLIST_NAME="com.youtube-watcher.bot"

if launchctl list 2>/dev/null | grep -q "$PLIST_NAME"; then
    echo "✅ YouTube Watcher Bot is RUNNING"
    echo ""
    echo "Process info:"
    launchctl list | grep "$PLIST_NAME"
    echo ""
    echo "Recent logs:"
    tail -5 /Users/artem_farafonov/Projects/youtube-watcher/logs/bot.log 2>/dev/null || echo "No log file yet"
    echo ""
    echo "Recent errors:"
    tail -5 /Users/artem_farafonov/Projects/youtube-watcher/logs/bot.err 2>/dev/null || echo "No error file yet"
else
    echo "❌ YouTube Watcher Bot is NOT running"
    echo ""
    echo "To start: ./scripts/start.sh"
    echo "To install: ./scripts/install.sh"
fi
