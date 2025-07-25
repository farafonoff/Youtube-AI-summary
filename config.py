import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
HF_TOKEN = os.getenv('HF_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
TELEGRAPH_TOKEN = os.getenv('TELEGRAPH_TOKEN')

# Paths
WHISPER_CLI_PATH = os.getenv('WHISPER_CLI_PATH', './whisper.cpp/build/bin/whisper-cli')
WHISPER_MODEL_PATH = os.getenv('WHISPER_MODEL_PATH', './whisper.cpp/models/ggml-small.bin')
YT_DLP_PATH = os.getenv('YT_DLP_PATH', './yt-dlp')

# Directories
DOWNLOADS_DIR = os.getenv('DOWNLOADS_DIR', './downloads')
TRANSCRIPTIONS_DIR = os.getenv('TRANSCRIPTIONS_DIR', './transcriptions')

# Ensure directories exist
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(TRANSCRIPTIONS_DIR, exist_ok=True)
