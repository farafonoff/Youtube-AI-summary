#!/usr/bin/env python3
"""
Test script for OpenRouter summarization service
"""

from openrouter_summarization_service import OpenRouterSummarizationService

def test_openrouter():
    """Test the OpenRouter service"""
    print("🧪 Testing OpenRouter summarization service...")
    
    try:
        service = OpenRouterSummarizationService()
        service_info = service.get_service_info()
        
        print(f"📊 Service Info:")
        for key, value in service_info.items():
            print(f"   {key}: {value}")
        
        if not service.is_initialized:
            print("⚠️  OpenRouter API key not configured")
            print("   Add your API key to OPENROUTER_API_KEY in .env file")
            print("   Get free API key at: https://openrouter.ai/")
            return False
        
        # Test with Russian text
        test_text = """
В 2023 году мировая экономика столкнулась с рядом вызовов, включая инфляцию, геополитическую нестабильность
и последствия пандемии. Страны по-разному справлялись с этими вызовами, принимая меры по стимулированию роста.
Центральные банки многих стран повышали процентные ставки для борьбы с инфляцией, что привело к замедлению
экономического роста. В то же время, развивающиеся страны сталкивались с дополнительными трудностями,
связанными с оттоком капитала и укреплением доллара США.
        """
        
        print(f"📝 Testing with text ({len(test_text.strip())} characters)...")
        summary = service.summarize_text(test_text.strip())
        
        print(f"✅ Summarization completed!")
        print(f"📄 Summary length: {len(summary)} characters")
        print(f"🎯 Summary:\n{summary}")
        
        return True
        
    except Exception as e:
        print(f"❌ OpenRouter test failed: {e}")
        return False

def test_with_long_text():
    """Test with longer text (existing transcription)"""
    print("\n🧪 Testing with long transcription...")
    
    try:
        import os
        txt_file = './transcriptions/audio_dVhYaEXir88.txt'
        
        if not os.path.exists(txt_file):
            print("⚠️  Long text file not found, skipping long text test")
            return True
        
        with open(txt_file, 'r', encoding='utf-8') as f:
            long_text = f.read().strip()
        
        service = OpenRouterSummarizationService()
        if not service.is_initialized:
            print("⚠️  OpenRouter not configured, skipping long text test")
            return True
        
        print(f"📝 Testing with long text ({len(long_text)} characters)...")
        summary = service.summarize_text(long_text)
        
        print(f"✅ Long text summarization completed!")
        print(f"📄 Summary length: {len(summary)} characters")
        print(f"🎯 Summary preview: {summary[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Long text test failed: {e}")
        return False

if __name__ == '__main__':
    print("🚀 OpenRouter Summarization Service Tests\n")
    
    success1 = test_openrouter()
    success2 = test_with_long_text()
    
    if success1 and success2:
        print("\n🎉 All OpenRouter tests passed!")
    else:
        print("\n⚠️  Some tests failed or were skipped")
