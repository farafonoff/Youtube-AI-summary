import os
import subprocess
import re
from config import YT_DLP_PATH, DOWNLOADS_DIR, FFPROBE_PATH


class YouTubeDownloader:
    def __init__(self):
        self.yt_dlp_path = YT_DLP_PATH
        self.downloads_dir = DOWNLOADS_DIR
    
    def extract_video_id(self, url):
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
            r'youtube\.com\/watch.*?[?&]v=([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_duration(self, youtube_url):
        """Get video duration in seconds using yt-dlp"""
        try:
            cmd = [self.yt_dlp_path, '--get-duration', youtube_url]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception:
            return None
    
    def get_audio_duration(self, audio_file_path):
        """Get audio duration in seconds using ffprobe"""
        try:
            cmd = [FFPROBE_PATH, '-v', 'error', '-show_entries', 'format=duration',
                   '-of', 'default=noprint_wrappers=1:nokey=1', audio_file_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return float(result.stdout.strip())
        except Exception:
            return None
    
    def download_audio(self, youtube_url):
        """Download audio from YouTube video, returns (audio_path, duration_seconds)"""
        try:
            video_id = self.extract_video_id(youtube_url)
            if not video_id:
                raise ValueError("Invalid YouTube URL")
            
            # Get expected duration
            expected_duration = self.get_duration(youtube_url)
            
            output_filename = f"audio_{video_id}.mp3"
            output_path = os.path.join(self.downloads_dir, output_filename)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                actual_duration = self.get_audio_duration(output_path)
                return output_path, actual_duration or expected_duration
            
            if os.path.exists(output_path):
                os.remove(output_path)
            
            cmd = [
                self.yt_dlp_path,
                '-x', '--audio-format', 'mp3',
                '-o', os.path.join(self.downloads_dir, f'audio_{video_id}.%(ext)s'),
                youtube_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                actual_duration = self.get_audio_duration(output_path)
                return output_path, actual_duration or expected_duration
            else:
                raise Exception(f"Audio file not created: {result.stderr}")
                
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to download audio: {e.stderr}")
        except Exception as e:
            raise Exception(f"Download error: {str(e)}")
