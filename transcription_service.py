import os
import subprocess
from config import WHISPER_CLI_PATH, WHISPER_MODEL_PATH, TRANSCRIPTIONS_DIR, FFPROBE_PATH


class TranscriptionService:
    def __init__(self):
        self.whisper_cli_path = WHISPER_CLI_PATH
        self.whisper_model_path = WHISPER_MODEL_PATH
        self.transcriptions_dir = TRANSCRIPTIONS_DIR
    
    def get_audio_duration(self, audio_file_path):
        """Get audio duration in seconds using ffprobe"""
        try:
            cmd = [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration',
                   '-of', 'default=noprint_wrappers=1:nokey=1', audio_file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception:
            return None
    
    def transcribe_audio(self, audio_file_path):
        """Transcribe audio file using whisper.cpp, returns (transcription, duration_seconds)"""
        try:
            base_name = os.path.splitext(os.path.basename(audio_file_path))[0]
            output_prefix = os.path.join(self.transcriptions_dir, base_name)
            txt_file = f"{output_prefix}.txt"
            
            if os.path.exists(txt_file) and os.path.getsize(txt_file) > 0:
                with open(txt_file, 'r', encoding='utf-8') as f:
                    transcription = f.read().strip()
                if transcription:
                    audio_duration = self.get_audio_duration(audio_file_path)
                    return transcription, audio_duration
                else:
                    print("⚠️ Existing transcription file is empty, re-transcribing...")
            
            cmd = [
                self.whisper_cli_path,
                '-m', self.whisper_model_path,
                '-l', 'auto',
                '--output-txt',
                '-of', output_prefix,
                '-f', audio_file_path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if os.path.exists(txt_file):
                with open(txt_file, 'r', encoding='utf-8') as f:
                    transcription = f.read().strip()
                audio_duration = self.get_audio_duration(audio_file_path)
                return transcription, audio_duration
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
