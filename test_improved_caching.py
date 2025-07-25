#!/usr/bin/env python3
"""
Test improved caching and error handling for the YouTube summarizer bot.
"""

import sys
import os
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_markdown_cleaning():
    """Test markdown cleaning functionality"""
    from openrouter_summarization_service import OpenRouterSummarizationService
    
    service = OpenRouterSummarizationService()
    
    # Test problematic markdown text
    test_text = """
# Main Header
This is **bold text** with *italic* and `code` blocks.

```python
def test():
    return "problematic"
```

- Bullet point with **bold**
- Another bullet • special character
- Third point with _underscores_

| Table | Header |
|-------|--------|
| Cell  | Data   |

[Link text](https://example.com)

Some text with strange characters: ♦ ♠ ♣ ♥

More text with underscores_like_this_pattern.
    """
    
    cleaned = service._clean_markdown_for_telegram(test_text)
    print("Original text:")
    print(test_text)
    print("\nCleaned text:")
    print(cleaned)
    print(f"\nCleaned text length: {len(cleaned)}")


def test_chunk_caching():
    """Test chunk summary caching"""
    from openrouter_summarization_service import OpenRouterSummarizationService
    
    service = OpenRouterSummarizationService()
    
    # Test video ID
    test_video_id = "test_video_123"
    
    # Test chunk summaries
    test_chunks = [
        "This is the first chunk summary about topic A.",
        "This is the second chunk summary about topic B.",
        "This is the third chunk summary about topic C."
    ]
    
    # Save chunk summaries
    print("Saving chunk summaries...")
    service._save_chunk_summaries_to_cache(test_video_id, test_chunks)
    
    # Load chunk summaries
    print("Loading chunk summaries...")
    loaded_chunks = service.get_cached_chunk_summaries(test_video_id)
    
    print(f"Saved chunks: {len(test_chunks)}")
    print(f"Loaded chunks: {len(loaded_chunks) if loaded_chunks else 0}")
    
    if loaded_chunks:
        print("Loaded chunk summaries:")
        for i, chunk in enumerate(loaded_chunks, 1):
            print(f"  Chunk {i}: {chunk}")
    else:
        print("❌ Failed to load chunk summaries")


def test_video_id_extraction():
    """Test video ID extraction from various URL formats"""
    import sys
    sys.path.append('.')
    
    from bot import extract_video_id
    
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ&t=123",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "youtube.com/watch?v=dQw4w9WgXcQ",
        "invalid_url_test"
    ]
    
    print("Testing video ID extraction:")
    for url in test_urls:
        video_id = extract_video_id(url)
        print(f"  {url} -> {video_id}")


def main():
    """Run all tests"""
    print("=== Testing Improved Caching and Error Handling ===\n")
    
    try:
        print("1. Testing Markdown Cleaning:")
        test_markdown_cleaning()
        print("\n" + "="*50 + "\n")
        
        print("2. Testing Chunk Caching:")
        test_chunk_caching()
        print("\n" + "="*50 + "\n")
        
        print("3. Testing Video ID Extraction:")
        test_video_id_extraction()
        print("\n" + "="*50 + "\n")
        
        print("✅ All tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
