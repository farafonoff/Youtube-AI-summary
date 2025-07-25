#!/usr/bin/env python3
"""
Test script for HuggingFace InferenceClient summarization
"""

from summarization_service import SummarizationService

def test_summarization():
    """Test the summarization service"""
    print("🧪 Testing HuggingFace InferenceClient summarization...")
    
    # Initialize service
    service = SummarizationService()
    
    # Test text (Russian as in your example)
    test_text = """
В 2023 году мировая экономика столкнулась с рядом вызовов, включая инфляцию, геополитическую нестабильность
и последствия пандемии. Страны по-разному справлялись с этими вызовами, принимая меры по стимулированию роста.
Центральные банки многих стран повышали процентные ставки для борьбы с инфляцией, что привело к замедлению
экономического роста. В то же время, развивающиеся страны сталкивались с дополнительными трудностями,
связанными с оттоком капитала и укреплением доллара США.
    """
    
    try:
        summary = service.summarize_text(test_text.strip())
        print(f"✅ Summarization successful!")
        print(f"📝 Original text length: {len(test_text.strip())} characters")
        print(f"📄 Summary length: {len(summary)} characters")
        print(f"🎯 Summary:\n{summary}")
        return True
    except Exception as e:
        print(f"❌ Summarization failed: {e}")
        return False

if __name__ == '__main__':
    success = test_summarization()
    if success:
        print("\n🎉 InferenceClient test passed!")
    else:
        print("\n❌ InferenceClient test failed!")
