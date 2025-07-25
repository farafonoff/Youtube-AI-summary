#!/usr/bin/env python3
"""
Test script to verify all components are working
"""

import os
import subprocess
from config import *

def test_yt_dlp():
    """Test yt-dlp functionality"""
    print("🧪 Testing yt-dlp...")
    try:
        result = subprocess.run([YT_DLP_PATH, '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ yt-dlp version: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ yt-dlp test failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ yt-dlp test error: {e}")
        return False

def test_whisper():
    """Test whisper-cli functionality"""
    print("🧪 Testing whisper-cli...")
    try:
        result = subprocess.run([WHISPER_CLI_PATH, '--help'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ whisper-cli is working")
            return True
        else:
            print(f"❌ whisper-cli test failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ whisper-cli test error: {e}")
        return False

def test_model():
    """Test if whisper model exists"""
    print("🧪 Testing whisper model...")
    if os.path.exists(WHISPER_MODEL_PATH):
        size = os.path.getsize(WHISPER_MODEL_PATH) / (1024 * 1024)  # MB
        print(f"✅ whisper model found ({size:.1f} MB)")
        return True
    else:
        print(f"❌ whisper model not found at: {WHISPER_MODEL_PATH}")
        return False

def test_directories():
    """Test if directories exist"""
    print("🧪 Testing directories...")
    dirs = [DOWNLOADS_DIR, TRANSCRIPTIONS_DIR]
    all_good = True
    for dir_path in dirs:
        if os.path.exists(dir_path):
            print(f"✅ Directory exists: {dir_path}")
        else:
            print(f"❌ Directory missing: {dir_path}")
            all_good = False
    return all_good

def test_tokens():
    """Test if tokens are configured"""
    print("🧪 Testing tokens...")
    if BOT_TOKEN and BOT_TOKEN != 'your_telegram_bot_token_here':
        print("✅ BOT_TOKEN is configured")
        bot_ok = True
    else:
        print("❌ BOT_TOKEN not configured")
        bot_ok = False
    
    if HF_TOKEN and HF_TOKEN != 'your_huggingface_token_here':
        print("✅ HF_TOKEN is configured")
        hf_ok = True
    else:
        print("❌ HF_TOKEN not configured")
        hf_ok = False
    
    return bot_ok and hf_ok

def main():
    """Run all tests"""
    print("🔧 Running component tests...\n")
    
    tests = [
        test_directories,
        test_yt_dlp,
        test_whisper,
        test_model,
        test_tokens
    ]
    
    results = []
    for test in tests:
        results.append(test())
        print()
    
    print("📊 Test Results:")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("🎉 All tests passed! Bot is ready to run.")
        print("To start the bot: python bot.py")
    else:
        print("❌ Some tests failed. Please fix the issues above.")
    
    return all(results)

if __name__ == '__main__':
    main()
