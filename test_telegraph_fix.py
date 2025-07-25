#!/usr/bin/env python3
"""
Test Telegraph service functionality
"""

import sys
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_telegraph_service():
    """Test Telegraph service functionality"""
    try:
        from telegraph_service import TelegraphService
        
        service = TelegraphService()
        
        # Test creating a page
        test_content = """
This is a test transcription from the YouTube summarizer bot.

Test paragraph 1: This is some sample content to test the Telegraph page creation.

Test paragraph 2: The bot should be able to create pages when transcriptions are too long for Telegram.

Test paragraph 3: This ensures users can still access full transcriptions even when they exceed Telegram's message limits.
        """
        
        print("Testing Telegraph page creation...")
        page_url = service.create_page(
            title="Test Transcription",
            content=test_content,
            video_url="https://youtube.com/watch?v=test123"
        )
        
        if page_url:
            print(f"✅ Telegraph page created successfully: {page_url}")
        else:
            print("❌ Telegraph page creation failed")
            
    except Exception as e:
        print(f"❌ Telegraph test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_telegraph_service()
