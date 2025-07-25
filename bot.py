import os
import telebot
from telebot import types
import logging
from youtube_downloader import YouTubeDownloader
from transcription_service import TranscriptionService
from summarization_service import SummarizationService
from openrouter_summarization_service import OpenRouterSummarizationService
from telegraph_service import TelegraphService
from config import BOT_TOKEN, DOWNLOADS_DIR, TRANSCRIPTIONS_DIR

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Initialize services
youtube_downloader = YouTubeDownloader()
transcription_service = TranscriptionService()
summarization_service = SummarizationService()
openrouter_service = OpenRouterSummarizationService()
telegraph_service = TelegraphService()


def send_message_with_fallback(bot, chat_id, text, parse_mode='Markdown'):
    """Send message with Markdown, fallback to plain text if parsing fails"""
    try:
        bot.send_message(chat_id, text, parse_mode=parse_mode)
    except Exception as e:
        logger.warning(f"Markdown parsing failed: {e}")
        try:
            # Remove common markdown formatting and try again
            clean_text = text.replace('**', '').replace('*', '').replace('_', '').replace('`', '')
            bot.send_message(chat_id, clean_text, parse_mode=None)
        except Exception as e2:
            logger.error(f"Failed to send message even without formatting: {e2}")
            # Last resort - send a generic error message
            bot.send_message(chat_id, "⚠️ Summary generated but couldn't be displayed due to formatting issues. Please try again.")


def send_summary_chunks(bot, chat_id, summary_text, service_name):
    """Send summary in chunks with proper handling for very long summaries"""
    try:
        # If summary is short enough, send directly with fallback
        if len(summary_text) <= 4096:
            send_message_with_fallback(bot, chat_id, summary_text)
            return
        
        # For very long summaries, try Telegraph first
        try:
            page_title = f"Video Summary - {service_name}"
            telegraph_url = telegraph_service.create_page(
                title=page_title,
                content=summary_text.replace(f"🎥 **Video Summary** (via {service_name}):\n\n", ""),
                video_url=None
            )
            
            if telegraph_url:
                bot.send_message(
                    chat_id,
                    f"🎥 **Video Summary** (via {service_name})\n\n"
                    f"The summary is too long for Telegram ({len(summary_text)} characters).\n"
                    f"You can read it here: {telegraph_url}",
                    parse_mode='Markdown'
                )
                return
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
                
                send_message_with_fallback(bot, chat_id, chunk_text)
                
            except Exception as chunk_error:
                logger.error(f"Error sending chunk {i+1}: {chunk_error}")
                # Try sending without any formatting as last resort
                try:
                    clean_chunk = chunk.replace('**', '').replace('*', '').replace('_', '').replace('`', '')
                    bot.send_message(chat_id, clean_chunk, parse_mode=None)
                except:
                    # If even that fails, send a simple error message
                    bot.send_message(chat_id, f"⚠️ Part {i+1} of summary couldn't be displayed due to formatting issues.")
        
    except Exception as e:
        logger.error(f"Error sending summary chunks: {e}")
        # Final fallback - send a simple message
        bot.send_message(chat_id, "⚠️ Summary generated but couldn't be displayed. Please try again or check logs.")


def extract_video_id(url):
    """Extract video ID from YouTube URL"""
    import re
    
    # Pattern for various YouTube URL formats
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com\/watch\?.*v=([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # If no pattern matches, try to extract any 11-character string that looks like a YouTube ID
    match = re.search(r'([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    # Fallback: use a hash of the URL if video ID can't be extracted
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()[:11]


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
/chunks <url|video_id> - Get cached chunk summaries

Just paste any YouTube URL to get started!

Note: Files are cached for faster processing on repeat requests.
Large videos are processed in chunks to save tokens and improve quality.
    """
    bot.reply_to(message, welcome_text)


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Handle all messages"""
    try:
        text = message.text.strip()
        
        # Check if message contains YouTube URL
        if 'youtube.com' in text or 'youtu.be' in text:
            process_youtube_video(message, text)
        else:
            bot.reply_to(message, "Please send a valid YouTube video URL.")
            
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        bot.reply_to(message, f"An error occurred: {str(e)}")


def process_youtube_video(message, youtube_url):
    """Process YouTube video: download, transcribe, and summarize"""
    try:
        # Extract video ID from URL for caching
        video_id = extract_video_id(youtube_url)
        
        # Send initial status
        status_message = bot.reply_to(message, "🔄 Processing your video...")
        
        # Step 1: Download audio
        bot.edit_message_text(
            "🔄 Checking/downloading audio from YouTube...",
            message.chat.id,
            status_message.message_id
        )
        
        audio_file_path = youtube_downloader.download_audio(youtube_url)
        logger.info(f"Audio ready: {audio_file_path}")
        
        # Step 2: Transcribe audio
        bot.edit_message_text(
            "🔄 Checking/transcribing audio using Whisper...",
            message.chat.id,
            status_message.message_id
        )
        
        transcription = transcription_service.transcribe_audio(audio_file_path)
        logger.info(f"Transcription completed, length: {len(transcription)} chars")
        
        # Step 3: Summarize text
        bot.edit_message_text(
            "🔄 Creating summary with AI...",
            message.chat.id,
            status_message.message_id
        )
        
        summary, service_used = smart_summarize(transcription, video_id=video_id)
        logger.info(f"Summary completed using {service_used}, length: {len(summary)} chars")
        
        # Send results
        bot.edit_message_text(
            "✅ Processing completed!",
            message.chat.id,
            status_message.message_id
        )
        
        # Send summary with robust chunking and Telegraph fallback
        summary_text = f"🎥 **Video Summary** (via {service_used}):\n\n{summary}"
        send_summary_chunks(bot, message.chat.id, summary_text, service_used)
        
        # Offer to send full transcription
        markup = types.InlineKeyboardMarkup()
        transcription_btn = types.InlineKeyboardButton(
            "📝 Get Full Transcription",
            callback_data=f"transcription_{os.path.basename(audio_file_path)}"
        )
        markup.add(transcription_btn)
        
        bot.send_message(
            message.chat.id,
            "Would you like to see the full transcription?",
            reply_markup=markup
        )
        
        # Cleanup - keep files by default for reuse
        cleanup_files(audio_file_path, force_cleanup=False)
        
    except Exception as e:
        logger.error(f"Error processing video: {e}")
        try:
            bot.edit_message_text(
                f"❌ Error: {str(e)}",
                message.chat.id,
                status_message.message_id
            )
        except:
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
                bot.send_message(
                    call.message.chat.id,
                    f"📝 **Full Transcription:**\n\n{transcription}",
                    parse_mode='Markdown'
                )
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


@bot.message_handler(commands=['services'])
def services_command(message):
    """Handle services command"""
    try:
        # Get service information
        openrouter_info = openrouter_service.get_service_info()
        
        services_text = f"""
🤖 **Available AI Services:**

**Primary Service:**
🔹 **OpenRouter** ({openrouter_info['model']})
   Status: {'✅ Ready' if openrouter_info['initialized'] else '❌ Not configured'}
   
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


def smart_summarize(text, video_id=None):
    """Smart summarization with OpenRouter primary and HuggingFace fallback"""
    try:
        # Try OpenRouter first
        if openrouter_service.is_initialized:
            logger.info("Attempting summarization with OpenRouter...")
            summary = openrouter_service.summarize_text(text, video_id=video_id)
            
            # Check if OpenRouter succeeded
            if summary and not any(error in summary.lower() for error in [
                'failed', 'error', 'timeout', 'not configured'
            ]):
                logger.info("✅ OpenRouter summarization successful")
                return summary, "OpenRouter (DeepSeek R1)"
        
        # Fallback to HuggingFace
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
    
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except Exception as e:
        logger.error(f"Bot polling error: {e}")


if __name__ == '__main__':
    main()
