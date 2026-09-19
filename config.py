import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
HF_TOKEN = os.getenv('HF_TOKEN')
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL')
TELEGRAPH_TOKEN = os.getenv('TELEGRAPH_TOKEN')

# Paths
WHISPER_CLI_PATH = os.getenv('WHISPER_CLI_PATH', './whisper.cpp/build/bin/whisper-cli')
WHISPER_MODEL_PATH = os.getenv('WHISPER_MODEL_PATH', './whisper.cpp/models/ggml-small.bin')
YT_DLP_PATH = os.getenv('YT_DLP_PATH', './yt-dlp')
FFPROBE_PATH = os.getenv('FFPROBE_PATH', 'ffprobe')

# Directories
DOWNLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
TRANSCRIPTIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'transcriptions')

# Ensure directories exist
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
os.makedirs(TRANSCRIPTIONS_DIR, exist_ok=True)
