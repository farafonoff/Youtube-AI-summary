#!/usr/bin/env python3
"""
Unit tests for YouTube Summarizer Bot
"""

# Test imports
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from openrouter_summarization_service import get_free_models, get_first_free_model, split_text_into_chunks, OpenRouterSummarizationService

# Clear cache before tests
import shutil
cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.cache')
if os.path.exists(cache_dir):
    shutil.rmtree(cache_dir)
    os.makedirs(cache_dir, exist_ok=True)

def test_get_free_models():
    """Test that get_free_models returns a non-empty list of model dicts with :free"""
    print("🧪 test_get_free_models...")
    models = get_free_models()
    assert isinstance(models, list), "Should return a list"
    assert len(models) > 0, "Should find at least one free model"
    for m in models:
        assert isinstance(m, dict), "Each model should be a dict"
        assert "id" in m
        assert m["id"].endswith(":free"), f"Model {m['id']} should end with :free"
    print(f"   ✅ Found {len(models)} free models")

def test_get_first_free_model():
    """Test that get_first_free_model returns a valid model string"""
    print("🧪 test_get_first_free_model...")
    model = get_first_free_model()
    assert isinstance(model, str), "Should return a string"
    assert model.endswith(":free"), f"Model {model} should end with :free"
    print(f"   ✅ Default model: {model}")

def test_split_text_into_chunks():
    """Test that split_text_into_chunks splits text correctly"""
    print("🧪 test_split_text_into_chunks...")
    text = "Hello world. " * 100  # ~1200 chars
    chunks = split_text_into_chunks(text, max_tokens=500, overlap=50)
    assert isinstance(chunks, list), "Should return a list"
    assert len(chunks) > 0, "Should have at least one chunk"
    # With small max_tokens, should have multiple chunks
    combined = "".join(chunks)
    assert len(combined) >= len(text) * 0.9, "Combined chunks should cover most of original text"
    print(f"   ✅ Split into {len(chunks)} chunks")

def test_split_text_into_chunks_default():
    """Test default chunking parameters"""
    print("🧪 test_split_text_into_chunks_default...")
    text = "Test text. " * 1000
    chunks = split_text_into_chunks(text)
    assert len(chunks) == 1, "Small text should fit in one chunk with default 250k tokens"
    print(f"   ✅ Default: 1 chunk for small text")

def test_service_init():
    """Test OpenRouterSummarizationService initialization"""
    print("🧪 test_service_init...")
    service = OpenRouterSummarizationService()
    assert service.is_initialized == (service.api_key is not None and service.api_key != "your_openrouter_api_key_here")
    assert hasattr(service, 'chunk_count'), "Should have chunk_count"
    assert hasattr(service, 'total_tokens'), "Should have total_tokens"
    assert hasattr(service, 'free_models'), "Should have free_models"
    assert isinstance(service.free_models, list), "free_models should be a list"
    print(f"   ✅ Service initialized, model={service.model}, free_models={len(service.free_models)}")

def test_service_get_service_info():
    """Test get_service_info returns expected keys"""
    print("🧪 test_service_get_service_info...")
    service = OpenRouterSummarizationService()
    info = service.get_service_info()
    assert "service" in info
    assert "model" in info
    assert "initialized" in info
    assert "api_configured" in info
    assert "free_models" in info
    assert isinstance(info["free_models"], list)
    print(f"   ✅ Service info has all keys")

def test_service_get_available_models():
    """Test get_available_models"""
    print("🧪 test_service_get_available_models...")
    service = OpenRouterSummarizationService()
    models = service.get_available_models()
    assert isinstance(models, list)
    for m in models:
        assert isinstance(m, dict), "Each model should be a dict with id and context_length"
        assert "id" in m
        assert "context_length" in m
    print(f"   ✅ Got {len(models)} models with context lengths")

def test_service_qa():
    """Test QA method"""
    print("🧪 test_service_qa...")
    service = OpenRouterSummarizationService()
    if not service.is_initialized:
        print("   ⚠️  Skipping Q&A test (no API key)")
        return
    answer = service.qa(question="What is the topic?", transcript="Test transcript about programming.", summary="Test summary.")
    assert isinstance(answer, str), "Answer should be a string"
    assert len(answer) > 0, "Answer should not be empty"
    print(f"   ✅ QA returned answer ({len(answer)} chars)")

def test_service_qa_no_api():
    """Test QA returns error when not initialized"""
    print("🧪 test_service_qa_no_api...")
    service = OpenRouterSummarizationService.__new__(OpenRouterSummarizationService)
    service.api_key = None
    service.model = "test"
    service.api_url = "https://openrouter.ai/api/v1/chat/completions"
    service.is_initialized = False
    answer = service.qa(question="Test?", transcript="Test", summary="Test")
    assert answer == "OpenRouter API key not configured"
    print(f"   ✅ QA properly returns error for unconfigured service")

def test_chunk_tracking():
    """Test that chunk_count and total_tokens are properly set after summarize_text"""
    print("🧪 test_chunk_tracking...")
    service = OpenRouterSummarizationService()
    service.chunk_count = 0
    service.total_tokens = 0
    text = "Hello world. " * 100
    result = service.summarize_text(text)
    assert service.chunk_count > 0, f"chunk_count should be > 0, got {service.chunk_count}"
    assert service.total_tokens > 0, f"total_tokens should be > 0, got {service.total_tokens}"
    assert isinstance(result, str) and len(result) > 0
    print(f"   ✅ chunk_count={service.chunk_count}, total_tokens={service.total_tokens}")

def test_create_summarization_prompt():
    """Test that the prompt is created correctly"""
    print("🧪 test_create_summarization_prompt...")
    service = OpenRouterSummarizationService.__new__(OpenRouterSummarizationService)
    text = "Test transcript text."
    prompt = service._create_summarization_prompt(text)
    assert text in prompt, "Original text should be in prompt"
    assert "Что за заголовком" in prompt, "Prompt should have the new output format"
    assert "🔑" in prompt, "Prompt should have analytical summary section"
    print(f"   ✅ Prompt created ({len(prompt)} chars)")

def test_bot_imports():
    """Test that bot module imports without errors"""
    print("🧪 test_bot_imports...")
    import bot
    assert hasattr(bot, 'bot'), "Should have bot instance"
    assert hasattr(bot, 'user_videos'), "Should have user_videos dict"
    assert hasattr(bot, 'message_video_map'), "Should have message_video_map dict"
    assert hasattr(bot, 'get_user_video'), "Should have get_user_video function"
    assert hasattr(bot, 'get_video_from_reply_chain'), "Should have get_video_from_reply_chain function"
    print(f"   ✅ Bot module imports correctly")

def test_bot_message_handler_order():
    """Test that command handlers are properly registered"""
    print("🧪 test_bot_message_handler_order...")
    import bot
    handlers = bot.bot.message_handlers
    command_handlers = [h for h in handlers if h.get('filters', {}).get('commands')]
    commands = []
    for h in command_handlers:
        cmds = h['filters']['commands']
        commands.extend(cmds)
    assert 'models' in commands, "models command should be registered"
    assert 'services' in commands, "services command should be registered"
    assert 'qa' not in commands, "qa command should be removed (use reply instead)"
    print(f"   ✅ Commands registered: {commands}")

def test_handler_logic():
    """Test handler logic without full bot import"""
    print("🧪 test_handler_logic...")
    # Test get_video_from_reply_chain
    class FakeReplyMsg:
        def __init__(self, msg_id, reply_to=None):
            self.message_id = msg_id
            self.reply_to_message = reply_to
    class FakeMessage:
        def __init__(self, reply_to=None):
            self.reply_to_message = reply_to
    
    message_video_map = {}
    def get_video_from_reply_chain(message):
        current = message
        while current and current.reply_to_message:
            msg_id = current.reply_to_message.message_id
            if msg_id in message_video_map:
                return message_video_map[msg_id]
            current = current.reply_to_message
        return None
    
    message_video_map[999] = 'abc123'
    parent = FakeReplyMsg(msg_id=999)
    child = FakeMessage(reply_to=parent)
    assert get_video_from_reply_chain(child) == 'abc123'
    
    # Test get_user_video
    user_videos = {}
    def get_user_video(user_id):
        if user_id in user_videos:
            return user_videos[user_id]["transcript"], user_videos[user_id]["summary"]
        return None, None
    
    user_videos[1] = {"transcript": "test", "summary": "sum"}
    t, s = get_user_video(1)
    assert t == "test" and s == "sum"
print("   ✅ Handler logic works")


def test_extract_video_id():
    """Test that extract_video_id only matches actual YouTube URLs, not random 11-char strings"""
    print("🧪 test_extract_video_id...")
    from bot import extract_video_id
    
    # Valid YouTube URLs
    assert extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == 'dQw4w9WgXcQ'
    assert extract_video_id("https://youtu.be/dQw4w9WgXcQ") == 'dQw4w9WgXcQ'
    assert extract_video_id("https://youtube.com/embed/dQw4w9WgXcQ") == 'dQw4w9WgXcQ'
    
    # Non-YouTube strings should return None (not false positives)
    assert extract_video_id("inclusionai") is None
    assert extract_video_id("just random text") is None
    assert extract_video_id("/not/a/youtube/url") is None
    
    # 🔖 marker should be recognized
    assert extract_video_id("🔖 video_id:dQw4w9WgXcQ") == 'dQw4w9WgXcQ'
    assert extract_video_id("text 🔖 video_id:dQw4w9WgXcQ more") == 'dQw4w9WgXcQ'
    
    print("   ✅ extract_video_id works correctly")


def test_reply_handler_exists():
    """Test that reply handler is registered"""
    print("🧪 test_reply_handler_exists...")
    import bot
    handlers = bot.bot.message_handlers
    # Look for the handle_reply function
    has_reply_handler = any('handle_reply' in str(h.get('function', '')) for h in handlers)
    assert has_reply_handler, "Should have a reply handler"
    # Verify no qa command handler
    all_commands = []
    for h in handlers:
        cmds = h.get('filters', {}).get('commands', [])
        all_commands.extend(cmds)
    assert 'qa' not in all_commands, "Should not have /qa command"
    print("   ✅ Reply handler registered, /qa command removed")

def test_transcript_reply_chain():
    """Test that reply chain traversal extracts video_id from original message text (no local cache needed)"""
    print("🧪 test_transcript_reply_chain...")
    import bot
    
    video_url = "🔖 video_id:dQw4w9WgXcQ"
    
    class FakeMsg:
        def __init__(self, msg_id, reply_to=None, text=""):
            self.message_id = msg_id
            self.reply_to_message = reply_to
            self.text = text
            self.caption = None
    
    # Chain: summary(101) -> original(100) -> None
    original_msg = FakeMsg(100, text=video_url)
    summary_msg = FakeMsg(101, reply_to=original_msg)
    
    # Replying to summary should find video_id marker in message text
    assert bot.get_video_from_reply_chain(summary_msg) == 'dQw4w9WgXcQ', \
        "Replying to summary should find video_id from message text"
    
    # Multi-step: Q&A reply(102) -> summary(101) -> original(100) -> None
    qa_reply = FakeMsg(102, reply_to=summary_msg)
    assert bot.get_video_from_reply_chain(qa_reply) == 'dQw4w9WgXcQ', \
        "Replying to Q&A answer should follow full chain to root"
    
    # Deeper: reply(103) -> qa_reply(102) -> summary(101) -> original(100) -> None
    deeper_reply = FakeMsg(103, reply_to=qa_reply)
    assert bot.get_video_from_reply_chain(deeper_reply) == 'dQw4w9WgXcQ', \
        "Deeper chain replies should still resolve to root video_id"
    
    # Test: even if message_video_map is empty, extraction from text still works
    bot.message_video_map.clear()
    assert bot.get_video_from_reply_chain(summary_msg) == 'dQw4w9WgXcQ', \
        "Should find video_id marker in text even with empty message_video_map"
    
    print("   ✅ Generic reply chain traversal works correctly")


def test_qa_reply_chain():
    """Test that Q&A answer is a reply to the user's question, preserving the full chain"""
    print("🧪 test_qa_reply_chain...")
    import bot
    
    video_url = "🔖 video_id:dQw4w9WgXcQ"
    
    class FakeMsg:
        def __init__(self, msg_id, reply_to=None, text=""):
            self.message_id = msg_id
            self.reply_to_message = reply_to
            self.text = text
            self.caption = None
    
    # Chain: user_question(100) <- summary(101) <- qa_question(102)
    # Answer is reply to qa_question(102)
    user_question = FakeMsg(100, text=video_url)  # original user message with video marker
    summary_msg = FakeMsg(101, reply_to=user_question)  # summary reply
    qa_question = FakeMsg(102, reply_to=summary_msg)  # user asks question about summary
    qa_answer = FakeMsg(103, reply_to=qa_question)  # bot's answer (reply to question)
    
    # Reply to answer should follow full chain to root video
    assert bot.get_video_from_reply_chain(qa_answer) == 'dQw4w9WgXcQ', \
        "Replying to Q&A answer should find video_id via full chain"
    
    # Also verify: user's question message itself doesn't need to be in message_video_map
    # because video_id marker is extracted from text
    assert bot.get_video_from_reply_chain(qa_question) == 'dQw4w9WgXcQ', \
        "Replying to Q&A question should also find video_id"
    
    # Clear message_video_map to verify text extraction works without cache
    bot.message_video_map.clear()
    assert bot.get_video_from_reply_chain(qa_answer) == 'dQw4w9WgXcQ', \
        "Should still work with empty message_video_map"
    
    print("   ✅ Q&A reply chain preserved correctly")


def test_send_summary_chunks_reply_to():
    """Test that send_summary_chunks passes reply_to_message_id and video_id through"""
    print("🧪 test_send_summary_chunks_reply_to...")
    import bot as bot_module
    
    class FakeBot:
        def __init__(self):
            self.sent = []
        def send_message(self, chat_id, text, **kwargs):
            self.sent.append((text, kwargs.get('reply_to_message_id')))
            return type('Msg', (), {'message_id': len(self.sent)})()
    
    fake_bot = FakeBot()
    msg = bot_module.send_summary_chunks(fake_bot, 1, "Short summary text", "test_service", video_id='vid1', reply_to_message_id=999)
    assert msg is not None
    assert fake_bot.sent[-1][1] == 999, f"reply_to_message_id should be passed through, got {fake_bot.sent[-1][1]}"
    assert '🔖 video_id:vid1' in fake_bot.sent[-1][0], f"🔖 video_id:vid1 should be in message text, got: {fake_bot.sent[-1][0]}"
    
    print("   ✅ send_summary_chunks passes reply_to_message_id and video_id correctly")


def test_send_message_with_fallback_video_id():
    """Test that send_message_with_fallback prepends [video_id:] marker"""
    print("🧪 test_send_message_with_fallback_video_id...")
    import bot as bot_module
    
    class FakeBot:
        def __init__(self):
            self.sent = []
        def send_message(self, chat_id, text, **kwargs):
            self.sent.append((text, kwargs.get('reply_to_message_id')))
            return type('Msg', (), {'message_id': len(self.sent)})()
    
    fake_bot = FakeBot()
    msg = bot_module.send_message_with_fallback(fake_bot, 1, "Test text", video_id='abc123')
    assert '🔖 video_id:abc123' in fake_bot.sent[-1][0], f"🔖 video_id:abc123 should be prepended"
    
    # Without video_id, no marker
    fake_bot.sent.clear()
    msg2 = bot_module.send_message_with_fallback(fake_bot, 1, "Test text")
    assert '🔖 video_id:' not in fake_bot.sent[-1][0], "No marker without video_id"
    
    print("   ✅ send_message_with_fallback prepends 🔖 video_id: correctly")


def test_persistent_cache():
    """Test that set_video_id persists to file and _load_video_id reads back"""
    print("🧪 test_persistent_cache...")
    import bot
    import os
    
    # Clean cache
    cache_dir = bot.CACHE_DIR
    for f in os.listdir(cache_dir):
        os.remove(os.path.join(cache_dir, f))
    
    # Set and load
    bot.set_video_id(123, 456, 'abc123')
    assert bot.message_video_map[456] == 'abc123'
    assert bot._load_video_id(456) == 'abc123'
    
    # Load from fresh module instance
    import importlib
    importlib.reload(bot)
    assert bot._load_video_id(456) == 'abc123'
    
    # Clean up
    for f in os.listdir(cache_dir):
        os.remove(os.path.join(cache_dir, f))
    
    print("   ✅ Persistent cache works across module reload")


def test_handle_reply_fallback():
    """Test that handle_reply falls back through all three methods to find video_id"""
    print("🧪 test_handle_reply_fallback...")
    import bot
    import os
    
    # Clean cache
    cache_dir = bot.CACHE_DIR
    for f in os.listdir(cache_dir):
        os.remove(os.path.join(cache_dir, f))
    
    class FakeMsg:
        def __init__(self, msg_id, reply_to=None, text=""):
            self.message_id = msg_id
            self.reply_to_message = reply_to
            self.text = text
            self.caption = None
    
    # Scenario: reply_to_message.text is None but file cache has video_id
    # Set up: answer message (id=200) has no text, but file cache has video_id
    video_id = 'abc123'
    bot.set_video_id(1, 200, video_id)
    
    answer_msg = FakeMsg(200, text=None)  # text is None (bot-sent message)
    reply = FakeMsg(201, reply_to=answer_msg)  # user replies to answer
    
    # Simulate handle_reply fallback logic
    vid = bot.get_video_from_reply_chain(reply)
    assert vid == video_id, f"Expected {video_id}, got {vid}"
    
    # Also test: reply_to_message.text has 🔖 marker
    bot.message_video_map.clear()
    answer_msg2 = FakeMsg(200, text=f"🔖 video_id:{video_id}")
    reply2 = FakeMsg(201, reply_to=answer_msg2)
    vid2 = bot.get_video_from_reply_chain(reply2)
    assert vid2 == video_id, f"Expected {video_id} from text marker, got {vid2}"
    
    # Clean up
    for f in os.listdir(cache_dir):
        os.remove(os.path.join(cache_dir, f))
    
    print("   ✅ handle_reply fallback chain works")


def test_main():
    """Run all tests"""
    tests = [
        test_get_free_models,
        test_get_first_free_model,
        test_split_text_into_chunks,
        test_split_text_into_chunks_default,
        test_service_init,
        test_service_get_service_info,
        test_service_get_available_models,
        test_chunk_tracking,
        test_create_summarization_prompt,
        test_bot_imports,
        test_bot_message_handler_order,
        test_handler_logic,
        test_extract_video_id,
        test_reply_handler_exists,
        test_transcript_reply_chain,
        test_send_summary_chunks_reply_to,
        test_qa_reply_chain,
        test_send_message_with_fallback_video_id,
        test_persistent_cache,
        test_handle_reply_fallback,
    ]

    results = []
    for test in tests:
        try:
            test()
            results.append(True)
        except Exception as e:
            print(f"   ❌ {test.__name__} failed: {e}")
            results.append(False)

    # Skip API-dependent tests if no key
    service = OpenRouterSummarizationService()
    if service.is_initialized:
        try:
            test_service_qa()
            results.append(True)
        except Exception as e:
            print(f"   ❌ test_service_qa failed: {e}")
            results.append(False)
        try:
            test_service_qa_no_api()
            results.append(True)
        except Exception as e:
            print(f"   ❌ test_service_qa_no_api failed: {e}")
            results.append(False)
    else:
        print("⚠️  Skipping API-dependent tests (no OpenRouter key)")
        results.append(True)  # Don't count as failure

    print(f"\n📊 Results: {sum(results)}/{len(results)} passed")
    if all(results):
        print("🎉 All tests passed!")
    else:
        print("❌ Some tests failed.")
        sys.exit(1)

if __name__ == '__main__':
    print("🚀 Unit Tests for YouTube Summarizer Bot\n")
    test_main()
