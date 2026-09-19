#!/usr/bin/env python3
"""
Convert .webm files to WAV format suitable for OpenRouter audio modality.

OpenRouter audio API expects:
- Format: WAV (PCM)
- Sample rate: 16 kHz
- Channels: Mono
- Bit depth: 16-bit
"""

import subprocess
import os
import glob
import sys

WEBMS_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_RATE = 16000
CHANNELS = 1


def convert_webm_to_wav(webm_path: str, output_dir: str = None) -> str:
    """Convert a single .webm file to 16kHz mono 16-bit WAV."""
    if output_dir is None:
        output_dir = WEBMS_DIR

    base_name = os.path.splitext(os.path.basename(webm_path))[0]
    wav_path = os.path.join(output_dir, f"{base_name}.wav")

    cmd = [
        "ffmpeg", "-y",
        "-i", webm_path,
        "-ar", str(SAMPLE_RATE),
        "-ac", str(CHANNELS),
        "-sample_fmt", "s16",
        "-c:a", "pcm_s16le",
        wav_path
    ]

    print(f"🔄 Converting: {os.path.basename(webm_path)} → {os.path.basename(wav_path)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Failed: {os.path.basename(webm_path)}")
        print(f"   stderr: {result.stderr.strip()}")
        return None

    file_size = os.path.getsize(wav_path) / (1024 * 1024)
    print(f"✅ Done: {os.path.basename(wav_path)} ({file_size:.1f} MB)")
    return wav_path


def main():
    webm_files = sorted(glob.glob(os.path.join(WEBMS_DIR, "*.webm")))

    if not webm_files:
        print("No .webm files found in:", WEBMS_DIR)
        sys.exit(1)

    print(f"Found {len(webm_files)} .webm file(s)\n")

    wav_files = []
    for webm_path in webm_files:
        wav_path = convert_webm_to_wav(webm_path)
        if wav_path:
            wav_files.append(wav_path)

    print(f"\n{'='*50}")
    print(f"Converted {len(wav_files)}/{len(webm_files)} files to WAV format")
    print(f"Files are in: {WEBMS_DIR}")
    print(f"\nTo use with OpenRouter, upload each .wav file as base64-encoded content")
    print(f"to the /v1/audio/transcriptions endpoint.")


if __name__ == "__main__":
    main()
