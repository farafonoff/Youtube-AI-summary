import os
import time
import json
import subprocess
import telebot
from telebot import types
import logging
from youtube_downloader import YouTubeDownloader
from transcription_service import TranscriptionService
from summarization_service import SummarizationService
from openrouter_summarization_service import OpenRouterSummarizationService, get_free_models
from telegraph_service import TelegraphService
from config import BOT_TOKEN, DOWNLOADS_DIR, TRANSCRIPTIONS_DIR, YT_DLP_PATH
import queue
import threading

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

import re as _re

def _safe_md(text):
    """Strip unbalanced markdown emphasis markers that cause Telegram API errors"""
    text = _re.sub(r'(?<!\*)\*(?!\*)', '', text)
    text = _re.sub(r'(?<!\w)_(?!\w)', '', text)
    return text

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Initialize services
youtube_downloader = YouTubeDownloader()
transcription_service = TranscriptionService()
summarization_service = SummarizationService()
openrouter_service = OpenRouterSummarizationService()
telegraph_service = TelegraphService()

from collections import deque
import queue
import threading

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.cache')
os.makedirs(CACHE_DIR, exist_ok=True)

def _load_video_id(message_id):
    filepath = os.path.join(CACHE_DIR, f"{message_id}.json")
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                data = json.load(f)
                return data.get('video_id')
    except Exception:
        pass
    return None

def _save_video_id(message_id, video_id):
    filepath = os.path.join(CACHE_DIR, f"{message_id}.json")
    try:
        with open(filepath, 'w') as f:
            json.dump({'video_id': video_id}, f)
    except Exception:
        pass

def set_video_id(chat_id, message_id, video_id):
    message_video_map[message_id] = video_id
    _save_video_id(message_id, video_id)

user_videos = {}  # {user_id: {"transcript": ..., "summary": ..., "video_id": ...}}
message_video_map = {}  # {message_id: video_id} (in-memory cache, persisted to files)
active_tasks = {}  # {task_id: {...}}
status_messages = {}  # {user_id: {task_id: message_id}}
task_queue = queue.Queue()  # Queue of task dicts
task_counter = 0
task_lock = threading.Lock()

def create_task(user_id, url, message_id, chat_id, status_msg=None):
    """Create a new task and add to queue"""
    global task_counter
    with task_lock:
        task_counter += 1
        task_id = task_counter
    
    task = {
        "task_id": task_id,
        "user_id": user_id,
        "chat_id": chat_id,
        "url": url,
        "message_id": message_id,
        "status_msg": status_msg,
        "status": "queued"
    }
    task_queue.put(task)
    active_tasks[task_id] = task
    return task_id

def get_next_task():
    """Get the next task from the queue"""
    try:
        return task_queue.get_nowait()
    except queue.Empty:
        return None

def mark_task_running(task_id):
    """Mark task as running"""
    if task_id in active_tasks:
        active_tasks[task_id]["status"] = "running"

def mark_task_done(task_id):
    """Mark task as done"""
    if task_id in active_tasks:
        active_tasks[task_id]["status"] = "done"
    task_queue.task_done()

def process_task_loop():
    """Background worker that processes tasks sequentially"""
    while True:
        task = get_next_task()
        if task is None:
            time.sleep(0.5)
            continue
        
        mark_task_running(task["task_id"])
        try:
            process_youtube_video_task(task)
        except Exception as e:
            logger.error(f"Task {task['task_id']} failed: {e}")
        finally:
            mark_task_done(task["task_id"])

def process_youtube_video_task(task):
    """Process a video task (download, transcribe, summarize) with progress updates"""
    user_id = task["user_id"]
    url = task["url"]
    message_id = task["message_id"]
    chat_id = task.get('chat_id', user_id)
    video_id = extract_video_id(url)
    
    # Store task info
    if message_id:
        set_video_id(chat_id, message_id, video_id)
    
    user_videos[user_id] = {"video_id": video_id}
    
    status_msg = task.get('status_msg')
    video_id_str = f"🔖 video_id:{video_id}" if video_id else ""
    
    def update_message(text):
        """Update the status message with progress"""
        try:
            if status_msg:
                bot.edit_message_text(f"{video_id_str}{text}", chat_id=chat_id, message_id=status_msg.message_id, parse_mode=None)
        except Exception as e:
            logger.debug(f"update_message failed: {e}")
            pass
    
    try:
        # Step 1: Download audio
        update_message("🔄 Downloading audio...")
        audio_file_path, audio_duration = youtube_downloader.download_audio(url)
        duration_str = f" [{audio_duration:.0f}s]" if audio_duration else ""
        logger.info(f"Audio ready: {audio_file_path}{duration_str}")
        
        # Step 2: Transcribe (with per-video lock)
        update_message(f"🔄 Transcribing with Whisper...{duration_str}")
        lock = get_video_lock(video_id)
        if lock.acquire(blocking=False):
            try:
                transcription, _ = transcription_service.transcribe_audio(audio_file_path)
                user_videos[user_id]["transcript"] = transcription
            finally:
                lock.release()
        else:
            logger.info(f"Video {video_id} already being transcribed, skipping")
            update_message("⚠️ This video is already being processed by another request.")
            return
        
        # Step 3: Summarize
        update_message("🔄 Creating summary with AI...")
        summary, service_used = smart_summarize(transcription, video_id=video_id)
        user_videos[user_id]["summary"] = summary
        
        # Step 4: Send results
        update_message(f"✅ Processing completed!{duration_str}")
        def fmt_duration(sec):
            if not sec:
                return "?"
            h, r = divmod(int(sec), 3600)
            m, s = divmod(r, 60)
            if h > 0:
                return f"{h}ч {m}м"
            return f"{m}м {s}с"
        dur_str = fmt_duration(audio_duration) if audio_duration else "?"
        summary_text = f"🎥 **Video Summary** (via {service_used}):\n\nЧанков: {openrouter_service.chunk_count}, Токенов: {openrouter_service.total_tokens}\nДлительность: {dur_str}\n\n{summary}"
        
        # Send summary as reply to original message to maintain reply chain
        original_message_id = task.get('message_id')
        summary_msg = send_summary_chunks(bot, user_id, summary_text, service_used, video_id=video_id, reply_to_message_id=original_message_id)
        if summary_msg:
            set_video_id(chat_id, summary_msg.message_id, video_id)
        
        # Offer to send full transcription
        base_name = f"audio_{video_id}"
        markup = types.InlineKeyboardMarkup()
        transcription_btn = types.InlineKeyboardButton(
            "📝 Get Full Transcription",
            callback_data=f"transcription_{base_name}"
        )
        markup.add(transcription_btn)
        bot.send_message(
            user_id,
            "Would you like to see the full transcription?",
            reply_markup=markup
        )
        
        # Cleanup
        cleanup_files(audio_file_path, force_cleanup=False)
        
        logger.info(f"Task {task['task_id']} completed: {service_used}")
    except Exception as e:
        logger.error(f"Task {task['task_id']} error: {e}")
        try:
            update_message(f"❌ Error: {str(e)}")
        except Exception:
            pass
        raise

def get_video_lock(video_id):
    """Get or create a threading lock for a video_id"""
    if video_id not in video_locks:
        video_locks[video_id] = threading.Lock()
    return video_locks[video_id]

video_locks = {}


def send_message_with_fallback(bot, chat_id, text, parse_mode='Markdown', reply_to_message_id=None, video_id=None):
    """Send message with Markdown, fallback to plain text if parsing fails"""
    import re as _re
    def _safe_md(t):
        # Escape unbalanced markdown emphasis markers that cause API errors
        t = _re.sub(r'(?<!\*)\*(?!\*)', '', t)
        t = _re.sub(r'(?<!\w)_(?!\w)', '', t)
        return t
    if video_id:
        text = f"🔖 video_id:{video_id}\n{text}"
    kwargs = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_to_message_id:
        kwargs["reply_to_message_id"] = reply_to_message_id
    try:
        msg = bot.send_message(**kwargs)
        return msg
    except Exception as e:
        logger.warning(f"Markdown parsing failed: {e}")
        logger.debug(f"Problematic message text (len={len(text)}): {text[:500]}")
        try:
            clean_text = _safe_md(text)
            if video_id:
                clean_text = f"🔖 video_id:{video_id}\n{clean_text}"
            kwargs2 = {"chat_id": chat_id, "text": clean_text, "parse_mode": None}
            if reply_to_message_id:
                kwargs2["reply_to_message_id"] = reply_to_message_id
            msg = bot.send_message(**kwargs2)
            return msg
        except Exception as e2:
            logger.error(f"Failed to send message even without formatting: {e2}")
            logger.debug(f"Problematic message text (len={len(text)}): {text[:500]}")
            fallback_text = "⚠️ Summary generated but couldn't be displayed."
            if video_id:
                fallback_text = f"🔖 video_id:{video_id}\n{fallback_text}"
            kwargs3 = {"chat_id": chat_id, "text": fallback_text}
            if reply_to_message_id:
                kwargs3["reply_to_message_id"] = reply_to_message_id
            msg = bot.send_message(**kwargs3)
            return msg


def send_summary_chunks(bot, chat_id, summary_text, service_name, video_id=None, reply_to_message_id=None):
    """Send summary in chunks with proper handling for very long summaries"""
    summary_text = _safe_md(summary_text)
    last_msg = None
    try:
        # If summary is short enough, send directly with fallback
        if len(summary_text) <= 4096:
            msg = send_message_with_fallback(bot, chat_id, summary_text, reply_to_message_id=reply_to_message_id, video_id=video_id)
            if video_id and msg:
                set_video_id(chat_id, msg.message_id, video_id)
            return msg
        
        # For very long summaries, try Telegraph first
        try:
            page_title = f"Video Summary - {service_name}"
            telegraph_url = telegraph_service.create_page(
                title=page_title,
                content=summary_text.replace(f"🎥 **Video Summary** (via {service_name}):\n\n", ""),
                video_url=None
            )
            
            if telegraph_url:
                msg = send_message_with_fallback(bot, chat_id,
                    f"🎥 **Video Summary** (via {service_name})\n\n"
                    f"The summary is too long for Telegram ({len(summary_text)} characters).\n"
                    f"You can read it here: {telegraph_url}",
                    video_id=video_id)
                if video_id and msg:
                    set_video_id(chat_id, msg.message_id, video_id)
                return msg
        except Exception as telegraph_error:
            logger.warning(f"Telegraph failed for summary: {telegraph_error}")
        
        # Fallback to chunked messages if Telegraph fails
        logger.info(f"Sending summary in chunks ({len(summary_text)} chars)")
        chunk_size = 3500  # Leave room for part numbering
        chunks = [summary_text[i:i+chunk_size] for i in range(0, len(summary_text), chunk_size)]
        
        for i, chunk in enumerate(chunks):
            try:
                if len(chunks) > 1:
                    prefix = f"**Part {i+1}/{len(chunks)}:**\n\n" if i > 0 else ""
                    chunk_text = f"{prefix}{chunk}"
                else:
                    chunk_text = chunk
                
                msg = send_message_with_fallback(bot, chat_id, chunk_text, video_id=video_id)
                if video_id and msg:
                    set_video_id(chat_id, msg.message_id, video_id)
                last_msg = msg
                
            except Exception as chunk_error:
                logger.error(f"Error sending chunk {i+1}: {chunk_error}")
                try:
                    clean_chunk = chunk.replace('**', '').replace('*', '').replace('_', '').replace('`', '')
                    msg = send_message_with_fallback(bot, chat_id, clean_chunk, video_id=video_id)
                    if video_id and msg:
                        set_video_id(chat_id, msg.message_id, video_id)
                    last_msg = msg
                except:
                    msg = send_message_with_fallback(bot, chat_id, f"⚠️ Part {i+1} of summary couldn't be displayed.", video_id=video_id)
                    if video_id and msg:
                        set_video_id(chat_id, msg.message_id, video_id)
                    last_msg = msg
        
        return last_msg
        
    except Exception as e:
        logger.error(f"Error sending summary chunks: {e}")
        # Final fallback - send a simple message
        msg = bot.send_message(chat_id, "⚠️ Summary generated but couldn't be displayed. Please try again or check logs.")
        if video_id and msg:
            set_video_id(chat_id, msg.message_id, video_id)
        return msg


def extract_video_id(url):
    """Extract video ID from a YouTube URL or 🔖 video_id: marker"""
    import re
    
    # Check for explicit video_id marker (🔖 video_id:xxx)
    match = re.search(r'🔖\s*video_id:([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    # Pattern for various YouTube URL formats
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Send welcome message"""
    welcome_text = """
🎥 YouTube Video Summarizer Bot

Send me a YouTube video link and I'll:
1. Download the audio
2. Transcribe it using Whisper
3. Create a summary for you

Commands:
/start - Show this message
/help - Show this message
/cleanup - Clean up cached files
/status - Show cache status
/services - Show available AI services
/models - List available free OpenRouter models
/chunks <url|video_id> - Get cached chunk summaries

💡 Reply to any summary/transcription message to ask a question about it.

Just paste any YouTube URL to get started!

Note: Files are cached for faster processing on repeat requests.
Large videos are processed in chunks to save tokens and improve quality.
    """
    bot.reply_to(message, welcome_text)


@bot.message_handler(func=lambda message: bool(message.reply_to_message and message.text and not message.text.startswith('/')))
def handle_reply(message):
    """Handle replies to video messages — auto Q&A if it looks like a question"""
    try:
        reply_to = message.reply_to_message
        logger.info(f"handle_reply: incoming msg_id={message.message_id}, reply_to_msg_id={reply_to.message_id if reply_to else None}, text={message.text[:60] if message.text else None}")
        video_id = get_video_from_reply_chain(message)
        logger.info(f"handle_reply: video_id from chain={video_id}")
        if not video_id and message.reply_to_message:
            video_id = extract_video_id(message.reply_to_message.text or message.reply_to_message.caption or "")
            logger.info(f"handle_reply: video_id from direct fallback={video_id}")
        if not video_id and message.reply_to_message:
            video_id = _load_video_id(message.reply_to_message.message_id)
            logger.info(f"handle_reply: video_id from file cache={video_id}")
        if not video_id:
            return
        
        text = message.text.strip()
        transcript = None
        summary = None

        try:
            cached_summary = openrouter_service._load_from_cache(video_id)
            if cached_summary:
                summary = cached_summary
            txt_file = os.path.join(transcription_service.transcriptions_dir, f"audio_{video_id}.txt")
            if os.path.exists(txt_file):
                with open(txt_file, 'r', encoding='utf-8') as f:
                    transcript = f.read().strip()
        except Exception:
            pass

        if not summary and not transcript:
            return

        bot.reply_to(message, "🔍 Thinking...")
        answer = openrouter_service.qa(question=text, transcript=transcript, summary=summary)

        answer_text = f"❓ **Question:** {text}\n\n**Answer:**\n{answer}"
        answer_msg = send_message_with_fallback(bot, message.chat.id, answer_text, reply_to_message_id=message.message_id, video_id=video_id)
        if answer_msg:
            set_video_id(message.chat.id, answer_msg.message_id, video_id)

    except Exception as e:
        logger.error(f"Reply handler error: {e}")


@bot.message_handler(func=lambda message: bool(message.text and not message.text.startswith('/')))
def handle_message(message):
    """Handle non-command messages"""
    try:
        text = message.text.strip()
        if 'youtube.com' in text or 'youtu.be' in text:
            process_youtube_video(message, text)
        else:
            bot.reply_to(message, "Please send a valid YouTube video URL.")
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        bot.reply_to(message, f"An error occurred: {str(e)}")


def process_youtube_video(message, youtube_url):
    """Create a processing task and add to queue"""
    try:
        video_id = extract_video_id(youtube_url)
        user_id = message.from_user.id
        chat_id = message.chat.id
        video_id_str = f"[video_id:{video_id}]"
        
        # Create initial status message
        status_msg = bot.reply_to(message, f"{video_id_str}⏳ Video queued (position 0). Processing will start shortly.")
        
        # Create task and add to queue, passing the status message
        task_id = create_task(user_id, youtube_url, message.message_id, chat_id, status_msg)
        
        # Update queue position
        try:
            bot.edit_message_text(f"{video_id_str}⏳ Video queued (position {task_queue.qsize()}). Processing will start shortly.",
                chat_id=chat_id, message_id=status_msg.message_id, parse_mode=None)
        except Exception:
            pass
        
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        bot.reply_to(message, f"❌ Error: {str(e)}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('transcription_'))
def handle_transcription_request(call):
    """Handle transcription button callback"""
    try:
        audio_filename = call.data.replace('transcription_', '')
        base_name = os.path.splitext(audio_filename)[0]
        txt_file = os.path.join(transcription_service.transcriptions_dir, f"{base_name}.txt")
        
        if os.path.exists(txt_file):
            with open(txt_file, 'r', encoding='utf-8') as f:
                transcription = f.read().strip()
            
            # Check if transcription is too long for Telegram (4096 char limit)
            if len(transcription) > 3500:  # Leave some room for formatting
                # Create Telegraph page for long transcription
                video_id = base_name.replace('audio_', '')
                page_title = f"Transcription - Video {video_id}"
                
                # Try to get original YouTube URL for reference
                youtube_url = f"https://youtube.com/watch?v={video_id}"
                
                telegraph_url = telegraph_service.create_page(
                    title=page_title,
                    content=transcription,
                    video_url=youtube_url
                )
                
                if telegraph_url:
                    bot.send_message(
                        call.message.chat.id,
                        f"📝 **Full Transcription**\n\n"
                        f"The transcription is too long for Telegram ({len(transcription)} characters).\n"
                        f"You can read it here: {telegraph_url}",
                        parse_mode='Markdown'
                    )
                else:
                    # Fallback to chunked messages if Telegraph fails
                    bot.send_message(
                        call.message.chat.id,
                        "📝 **Full Transcription** (Telegraph failed, sending in chunks):"
                    )
                    send_transcription_chunks(call.message.chat.id, transcription)
            else:
                # Send directly if short enough
                msg = bot.send_message(
                    call.message.chat.id,
                    f"📝 **Full Transcription:**\n\n{transcription}",
                    parse_mode='Markdown'
                )
                set_video_id(call.message.chat.id, msg.message_id, video_id)
        else:
            bot.send_message(call.message.chat.id, "Transcription file not found.")
            
        bot.answer_callback_query(call.id)
        
    except Exception as e:
        logger.error(f"Error sending transcription: {e}")
        bot.answer_callback_query(call.id, "Error retrieving transcription")


def send_transcription_chunks(chat_id, transcription):
    """Send transcription in chunks if Telegraph fails"""
    try:
        chunk_size = 3500
        chunks = [transcription[i:i+chunk_size] for i in range(0, len(transcription), chunk_size)]
        
        for i, chunk in enumerate(chunks):
            prefix = f"**Part {i+1}/{len(chunks)}:**\n\n" if len(chunks) > 1 else ""
            bot.send_message(chat_id, f"{prefix}{chunk}", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error sending chunks: {e}")
        # Final fallback - plain text
        bot.send_message(chat_id, transcription)


def cleanup_files(audio_file_path, force_cleanup=False):
    """Clean up downloaded files - by default keeps files for reuse"""
    try:
        if not force_cleanup:
            logger.info(f"Keeping files for reuse: {audio_file_path}")
            return
            
        # Remove audio file only if force_cleanup is True
        if os.path.exists(audio_file_path):
            os.remove(audio_file_path)
            logger.info(f"Cleaned up audio file: {audio_file_path}")
        
        # Clean up transcription files only if force_cleanup is True
        transcription_service.cleanup_transcription_files(audio_file_path)
        logger.info("Cleaned up transcription files")
        
    except Exception as e:
        logger.error(f"Cleanup error: {e}")


@bot.message_handler(commands=['cleanup'])
def cleanup_command(message):
    """Handle cleanup command"""
    try:
        # Count files before cleanup
        audio_files = len([f for f in os.listdir(DOWNLOADS_DIR) if f.endswith('.mp3')])
        txt_files = len([f for f in os.listdir(TRANSCRIPTIONS_DIR) if f.endswith('.txt')])
        
        # Clean up all files
        for filename in os.listdir(DOWNLOADS_DIR):
            if filename.endswith('.mp3'):
                file_path = os.path.join(DOWNLOADS_DIR, filename)
                os.remove(file_path)
        
        for filename in os.listdir(TRANSCRIPTIONS_DIR):
            if filename.endswith('.txt'):
                file_path = os.path.join(TRANSCRIPTIONS_DIR, filename)
                os.remove(file_path)
        
        bot.reply_to(message, f"🧹 Cleanup complete!\nRemoved {audio_files} audio files and {txt_files} transcription files.")
        
    except Exception as e:
        logger.error(f"Cleanup command error: {e}")
        bot.reply_to(message, f"❌ Cleanup failed: {str(e)}")


@bot.message_handler(commands=['chunks'])
def chunks_command(message):
    """Handle chunks command to retrieve cached chunk summaries"""
    try:
        # Get the video ID from the message (user should provide YouTube URL or video ID)
        args = message.text.split()[1:] if len(message.text.split()) > 1 else []
        
        if not args:
            bot.reply_to(message, "❌ Please provide a YouTube URL or video ID.\nExample: `/chunks https://youtube.com/watch?v=VIDEO_ID`")
            return
        
        url_or_id = args[0]
        
        # Extract video ID if it's a URL
        if 'youtube.com' in url_or_id or 'youtu.be' in url_or_id:
            video_id = extract_video_id(url_or_id)
        else:
            video_id = url_or_id
        
        # Try to get cached chunk summaries
        chunk_summaries = openrouter_service.get_cached_chunk_summaries(video_id)
        
        if chunk_summaries:
            response = f"📝 **Cached Chunk Summaries for {video_id}:**\n\n"
            
            for i, chunk_summary in enumerate(chunk_summaries, 1):
                response += f"**Chunk {i}:**\n{chunk_summary}\n\n"
            
            # Use robust chunking for long responses
            send_summary_chunks(bot, message.chat.id, response, "Cache")
        else:
            bot.reply_to(message, f"❌ No cached chunk summaries found for video ID: {video_id}")
        
    except Exception as e:
        logger.error(f"Chunks command error: {e}")
        bot.reply_to(message, f"❌ Chunks retrieval failed: {str(e)}")


@bot.message_handler(commands=['status'])
def status_command(message):
    """Handle status command"""
    try:
        # Count cached files
        audio_files = [f for f in os.listdir(DOWNLOADS_DIR) if f.endswith('.mp3')]
        txt_files = [f for f in os.listdir(TRANSCRIPTIONS_DIR) if f.endswith('.txt')]
        
        # Calculate total size
        total_size = 0
        for filename in audio_files:
            file_path = os.path.join(DOWNLOADS_DIR, filename)
            total_size += os.path.getsize(file_path)
        
        size_mb = total_size / (1024 * 1024)
        
        status_text = f"""
📊 Cache Status:
🎵 Audio files: {len(audio_files)}
📝 Transcription files: {len(txt_files)}
💾 Total size: {size_mb:.1f} MB

Use /cleanup to clear cache if needed.
        """
        
        bot.reply_to(message, status_text)
        
    except Exception as e:
        logger.error(f"Status command error: {e}")
        bot.reply_to(message, f"❌ Status check failed: {str(e)}")


@bot.message_handler(commands=['models'])
def models_command(message):
    """Handle models command to list available free OpenRouter models"""
    try:
        free_models = openrouter_service.free_models
        if not free_models:
            free_models = get_free_models()
            openrouter_service.free_models = free_models

        if not free_models:
            bot.reply_to(message, "❌ Could not fetch free models.")
            return

        models_text = f"🆓 **Available Free OpenRouter Models** ({len(free_models)} total):\n\n"
        for m in free_models:
            model_id = m["id"]
            ctx = m.get("context_length", "?")
            models_text += f"• `{model_id}` — {ctx} tokens\n"

        bot.reply_to(message, models_text, parse_mode=None)

    except Exception as e:
        logger.error(f"Models command error: {e}")
        bot.reply_to(message, f"❌ Failed to fetch models: {str(e)}")


def get_video_from_reply_chain(message):
    """Recursively trace reply_to_message chain to find video_id"""
    current = message
    visited = set()
    while current and current.message_id not in visited:
        visited.add(current.message_id)
        current_text = current.text or current.caption or ""
        video_id = extract_video_id(current_text)
        if video_id:
            return video_id
        if current.message_id in message_video_map:
            return message_video_map[current.message_id]
        # Check file cache for reply_to_message if text is not available
        if current.reply_to_message:
            cached = _load_video_id(current.reply_to_message.message_id)
            if cached:
                return cached
        if not current.reply_to_message:
            break
        current = current.reply_to_message
    return None


def get_user_video(user_id):
    """Get user's video data from in-memory cache"""
    if user_id in user_videos:
        return user_videos[user_id]["transcript"], user_videos[user_id]["summary"]
    return None, None


@bot.message_handler(commands=['services'])
def services_command(message):
    """Handle services command"""
    try:
        openrouter_info = openrouter_service.get_service_info()
        
        free_models_text = "\n".join([f"  • {m}" for m in openrouter_info.get('free_models', [])[:10]])
        if len(openrouter_info.get('free_models', [])) > 10:
            free_models_text += f"\n  ... and {len(openrouter_info['free_models']) - 10} more"
        
        services_text = f"""
🤖 **Available AI Services:**

**Primary Service:**
🔹 **OpenRouter** ({openrouter_info['model']})
   Status: {'✅ Ready' if openrouter_info['initialized'] else '❌ Not configured'}

**Free Models:**
{free_models_text}

**Fallback Service:**
🔹 **HuggingFace** (RuT5 Base Gazeta)
   Status: ✅ Ready

**Service Selection:**
The bot automatically tries OpenRouter first for better quality summaries, then falls back to HuggingFace if needed.

To configure OpenRouter: Add your API key to OPENROUTER_API_KEY in .env file.
Get free API key at: https://openrouter.ai/
        """
        
        bot.reply_to(message, services_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Services command error: {e}")
        bot.reply_to(message, f"❌ Services check failed: {str(e)}")


@bot.message_handler(commands=['update'])
def update_command(message):
    """Update yt-dlp"""
    try:
        bot.reply_to(message, "🔄 Updating yt-dlp...")
        result = subprocess.run(
            [YT_DLP_PATH, '--update'],
            capture_output=True, text=True, check=True
        )
        bot.reply_to(message, f"✅ yt-dlp updated successfully\n{result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Update failed: {e.stderr}")
        bot.reply_to(message, f"❌ yt-dlp update failed: {e.stderr.strip()}")
    except Exception as e:
        logger.error(f"Update error: {e}")
        bot.reply_to(message, f"❌ Update error: {str(e)}")


def smart_summarize(text, video_id=None):
    """Smart summarization with OpenRouter primary and HuggingFace fallback"""
    try:
        if openrouter_service.is_initialized:
            logger.info("Attempting summarization with OpenRouter...")
            summary = openrouter_service.summarize_text(text, video_id=video_id)
            
            if summary and not any(error in summary.lower() for error in [
                'failed', 'error', 'timeout', 'not configured'
            ]):
                logger.info("✅ OpenRouter summarization successful")
                cc = openrouter_service.chunk_count
                tc = openrouter_service.total_tokens
                return summary, f"OpenRouter ({openrouter_service.model}) [chunks: {cc}, tokens: {tc}]"
        
        logger.info("Falling back to HuggingFace summarization...")
        hf_summary = summarization_service.summarize_text(text)
        return hf_summary, "HuggingFace (RuT5)"
        
    except Exception as e:
        logger.error(f"Smart summarization error: {e}")
        return f"Summarization failed: {str(e)}", "Error"


def main():
    """Main function to start the bot"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN not found in environment variables")
        return
    
    logger.info("Starting YouTube Summarizer Bot...")
    
    # Start background task processor
    worker = threading.Thread(target=process_task_loop, daemon=True)
    worker.start()
    logger.info("✅ Task processor started")
    
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        logger.error(f"Bot polling error: {e}")


if __name__ == '__main__':
    main()
