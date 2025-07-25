#!/usr/bin/env python3
"""
Test script for Telegraph service
"""

from telegraph_service import TelegraphService

def test_telegraph():
    """Test the Telegraph service"""
    print("🧪 Testing Telegraph service...")
    
    try:
        service = TelegraphService()
        
        # Test with the existing transcription
        with open('./transcriptions/audio_dVhYaEXir88.txt', 'r', encoding='utf-8') as f:
            content = f.read()
        
        title = "Test Transcription - Yulia Latynina"
        video_url = "https://youtube.com/watch?v=dVhYaEXir88"
        
        telegraph_url = service.create_page(title, content, video_url)
        
        if telegraph_url:
            print(f"✅ Telegraph page created successfully!")
            print(f"🔗 URL: {telegraph_url}")
            print(f"📊 Content length: {len(content)} characters")
            return True
        else:
            print("❌ Failed to create Telegraph page")
            return False
            
    except Exception as e:
        print(f"❌ Telegraph test failed: {e}")
        return False

if __name__ == '__main__':
    success = test_telegraph()
    if success:
        print("\n🎉 Telegraph test passed!")
    else:
        print("\n❌ Telegraph test failed!")
