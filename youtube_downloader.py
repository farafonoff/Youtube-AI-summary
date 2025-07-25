import os
import subprocess
import re
from config import YT_DLP_PATH, DOWNLOADS_DIR


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
    
    def download_audio(self, youtube_url):
        """Download audio from YouTube video"""
        try:
            video_id = self.extract_video_id(youtube_url)
            if not video_id:
                raise ValueError("Invalid YouTube URL")
            
            # Use predictable filename
            output_filename = f"audio_{video_id}.mp3"
            output_path = os.path.join(self.downloads_dir, output_filename)
            
            # Check if file already exists and is not empty
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                print(f"✅ Audio file already exists: {output_path}")
                return output_path
            
            # Remove existing file if it exists but is empty
            if os.path.exists(output_path):
                os.remove(output_path)
            
            print(f"🔄 Downloading audio for video ID: {video_id}")
            
            # Download command
            cmd = [
                self.yt_dlp_path,
                '-x',
                '--audio-format', 'mp3',
                '-o', os.path.join(self.downloads_dir, f'audio_{video_id}.%(ext)s'),
                youtube_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if os.path.exists(output_path):
                return output_path
            else:
                raise Exception(f"Audio file not created: {result.stderr}")
                
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to download audio: {e.stderr}")
        except Exception as e:
            raise Exception(f"Download error: {str(e)}")
