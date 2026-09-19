#!/bin/bash

# Startup script for YouTube Telegram Bot

echo "🤖 Starting YouTube Telegram Bot..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy .env.example to .env and configure your tokens:"
    echo "cp .env.example .env"
    exit 1
fi

# Check if BOT_TOKEN is set
if grep -q "your_telegram_bot_token_here" .env; then
    echo "❌ Error: Please set your BOT_TOKEN in .env file"
    echo "Get your bot token from @BotFather on Telegram"
    exit 1
fi

# Check if required files exist
if [ ! -f ./whisper.cpp/build/bin/whisper-cli ]; then
    echo "❌ Error: whisper-cli not found at ./whisper.cpp/build/bin/whisper-cli"
    exit 1
fi

if [ ! -f ./whisper.cpp/models/ggml-small.bin ]; then
    echo "❌ Error: whisper model not found at ./whisper.cpp/models/ggml-small.bin"
    exit 1
fi

if [ ! -f ./yt-dlp ]; then
    echo "❌ Error: yt-dlp not found at ./yt-dlp"
    exit 1
fi

echo "✅ All dependencies found"
echo "🚀 Starting bot..."

source ./bin/activate 2>/dev/null || true
python3 bot.py
