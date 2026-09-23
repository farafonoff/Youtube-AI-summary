#!/bin/bash
set -e

PROJECT_DIR="/Users/artem_farafonov/Projects/youtube-watcher"
PLIST_NAME="com.youtube-watcher.bot"
LAUNCH_AGENT_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$LAUNCH_AGENT_DIR/$PLIST_NAME.plist"

echo "📦 Installing YouTube Watcher Bot as a macOS LaunchAgent..."

# Check if project exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Error: Project directory not found at $PROJECT_DIR"
    exit 1
fi

# Check if .env exists
if [ ! -f "$PROJECT_DIR/.env" ]; then
    echo "⚠️  Warning: .env file not found. Copying from .env.example..."
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo "⚠️  Please edit .env with your tokens before starting the bot!"
fi

# Check if whisper-cli exists
if [ ! -f "$PROJECT_DIR/whisper.cpp/build/bin/whisper-cli" ]; then
    echo "⚠️  Warning: whisper-cli not found at $PROJECT_DIR/whisper.cpp/build/bin/whisper-cli"
    echo "⚠️  You need to build whisper.cpp before starting the bot."
fi

# Check if yt-dlp exists
if [ ! -f "$PROJECT_DIR/yt-dlp" ]; then
    echo "⚠️  Warning: yt-dlp not found at $PROJECT_DIR/yt-dlp"
fi

# Check if virtual environment exists
if [ ! -f "$PROJECT_DIR/bin/activate" ]; then
    echo "⚠️  Warning: Virtual environment not found at $PROJECT_DIR/bin/activate"
    echo "💡 Run: cd $PROJECT_DIR && python3 -m venv bin && pip install -r requirements.txt"
fi

# Create logs directory
mkdir -p "$PROJECT_DIR/logs"

# Copy plist to LaunchAgents
echo "📝 Installing LaunchAgent plist..."
cp "$PROJECT_DIR/$PLIST_NAME.plist" "$PLIST_PATH"

# Unload existing service if running
launchctl unload "$PLIST_PATH" 2>/dev/null || true

# Load and start the service
launchctl load "$PLIST_PATH"
launchctl start "$PLIST_NAME"

echo ""
echo "✅ Installation complete!"
echo "🚀 YouTube Watcher Bot is now running in the background."
echo ""
echo "Commands:"
echo "  ./scripts/start.sh   - Start the bot"
echo "  ./scripts/stop.sh    - Stop the bot"
echo "  ./scripts/status.sh  - Check bot status"
echo "  ./scripts/uninstall.sh - Remove the service"
echo ""
echo "Logs:"
echo "  tail -f logs/bot.log"
echo "  tail -f logs/bot.err"
