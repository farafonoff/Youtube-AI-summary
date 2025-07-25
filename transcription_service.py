import os
import subprocess
from config import WHISPER_CLI_PATH, WHISPER_MODEL_PATH, TRANSCRIPTIONS_DIR


class TranscriptionService:
    def __init__(self):
        self.whisper_cli_path = WHISPER_CLI_PATH
        self.whisper_model_path = WHISPER_MODEL_PATH
        self.transcriptions_dir = TRANSCRIPTIONS_DIR
    
    def transcribe_audio(self, audio_file_path):
        """Transcribe audio file using whisper.cpp"""
        try:
            # Extract filename without extension
            base_name = os.path.splitext(os.path.basename(audio_file_path))[0]
            output_prefix = os.path.join(self.transcriptions_dir, base_name)
            txt_file = f"{output_prefix}.txt"
            
            # Check if transcription already exists and is not empty
            if os.path.exists(txt_file) and os.path.getsize(txt_file) > 0:
                print(f"✅ Transcription file already exists: {txt_file}")
                with open(txt_file, 'r', encoding='utf-8') as f:
                    transcription = f.read().strip()
                if transcription:  # Make sure it's not just whitespace
                    return transcription
                else:
                    print("⚠️ Existing transcription file is empty, re-transcribing...")
            
            print(f"🔄 Transcribing audio file: {audio_file_path}")
            
            # Whisper command
            cmd = [
                self.whisper_cli_path,
                '-m', self.whisper_model_path,
                '-l', 'auto',  # Auto-detect language
                '--output-txt',
                '-of', output_prefix,  # Output file prefix
                '-f', audio_file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # Read the generated text file
            if os.path.exists(txt_file):
                with open(txt_file, 'r', encoding='utf-8') as f:
                    transcription = f.read().strip()
                return transcription
            else:
                raise Exception("Transcription file not created")
                
        except subprocess.CalledProcessError as e:
            raise Exception(f"Transcription failed: {e.stderr}")
        except Exception as e:
            raise Exception(f"Transcription error: {str(e)}")
    
    def cleanup_transcription_files(self, audio_file_path):
        """Clean up transcription files"""
        try:
            base_name = os.path.splitext(os.path.basename(audio_file_path))[0]
            txt_file = os.path.join(self.transcriptions_dir, f"{base_name}.txt")
            if os.path.exists(txt_file):
                os.remove(txt_file)
        except Exception:
            pass  # Ignore cleanup errors
