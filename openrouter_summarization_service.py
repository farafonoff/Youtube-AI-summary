import requests
import json
import logging
import os
import tiktoken
from config import OPENROUTER_API_KEY

logger = logging.getLogger(__name__)


def split_text_into_chunks(text, max_tokens=15000, overlap=1000, model="gpt-4o"):
    """
    Split text into chunks based on token count rather than character count.
    This ensures we don't exceed model token limits and provides better chunking.
    """
    try:
        enc = tiktoken.encoding_for_model(model)
        tokens = enc.encode(text)
        
        chunks = []
        start = 0
        while start < len(tokens):
            end = min(start + max_tokens, len(tokens))
            chunk = enc.decode(tokens[start:end])
            chunks.append(chunk)
            start += max_tokens - overlap  # move forward with overlap
        
        return chunks
    except Exception as e:
        logger.warning(f"Tiktoken chunking failed: {e}, falling back to character-based chunking")
        # Fallback to character-based chunking
        max_chars = max_tokens * 4  # Rough approximation: 4 chars per token
        overlap_chars = overlap * 4
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + max_chars, len(text))
            chunk = text[start:end]
            chunks.append(chunk)
            start += max_chars - overlap_chars
        return chunks


class OpenRouterSummarizationService:
    def __init__(self):
        self.api_key = OPENROUTER_API_KEY
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.model = "deepseek/deepseek-r1-0528:free"
        self.is_initialized = self._check_api_key()
    
    def _check_api_key(self):
        """Check if OpenRouter API key is configured"""
        if not self.api_key or self.api_key == "your_openrouter_api_key_here":
            logger.warning("❌ OpenRouter API key not configured")
            return False
        logger.info("✅ OpenRouter summarization service initialized")
        return True
    
    def summarize_text(self, text, video_id=None):
        """Summarize the given text using OpenRouter API with caching"""
        if not self.is_initialized:
            return "OpenRouter API key not configured"
        
        if not text or len(text.strip()) < 50:
            return "Text too short to summarize."
        
        # Try to load from cache first
        if video_id:
            cached_summary = self._load_from_cache(video_id)
            if cached_summary:
                return cached_summary
        
        try:
            # For very long texts, split into chunks using intelligent token-based chunking
            max_tokens = 15000  # DeepSeek R1 can handle up to ~30k tokens, leave room for response
            if len(text) > max_tokens * 3:  # Rough estimate: 3 chars per token
                summary = self._summarize_long_text(text, max_tokens, video_id)
            else:
                summary = self._summarize_single_chunk(text)
            
            # Save to cache if video_id provided
            if video_id and summary and not summary.startswith("Summarization failed"):
                self._save_to_cache(video_id, summary)
            
            return summary
                
        except Exception as e:
            logger.error(f"OpenRouter summarization failed: {e}")
            return f"Summarization failed: {str(e)}"
    
    def _summarize_single_chunk(self, text):
        """Summarize a single chunk of text"""
        try:
            # Create the prompt for summarization
            prompt = self._create_summarization_prompt(text)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/youtube-summarizer-bot",
                "X-Title": "YouTube Summarizer Bot"
            }
            
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 8192,  # Adjust based on model limits
                "temperature": 0.1,
                "top_p": 0.9
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    summary = result['choices'][0]['message']['content'].strip()
                    # Clean up Markdown for Telegram
                    summary = self._clean_markdown_for_telegram(summary)
                    logger.info(f"✅ OpenRouter summarization successful ({len(summary)} chars)")
                    return summary
                else:
                    return "No summary generated by OpenRouter"
            else:
                logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
                return f"API error: {response.status_code}"
                
        except requests.exceptions.Timeout:
            return "Summarization timeout - text may be too long"
        except Exception as e:
            logger.error(f"OpenRouter API request failed: {e}")
            return f"Request failed: {str(e)}"
    
    def _summarize_long_text(self, text, max_tokens, video_id=None):
        """Summarize very long text by splitting into intelligent token-based chunks"""
        try:
            # Split text into chunks using tiktoken for accurate token counting
            chunks = split_text_into_chunks(text, max_tokens=max_tokens, overlap=1000)
            logger.info(f"Splitting long text into {len(chunks)} chunks using intelligent token-based chunking")
            
            # Check if we have cached chunk summaries first
            if video_id:
                cached_chunk_summaries = self._load_chunk_summaries_from_cache(video_id)
                if cached_chunk_summaries:
                    logger.info(f"✅ Using {len(cached_chunk_summaries)} cached chunk summaries")
                    summaries = cached_chunk_summaries
                else:
                    # Process chunks and cache them
                    summaries = []
                    chunk_summaries = []
                    
                    for i, chunk in enumerate(chunks):
                        if len(chunk.strip()) > 50:
                            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
                            summary = self._summarize_single_chunk(chunk)
                            if summary and not summary.startswith("Summarization failed"):
                                summaries.append(summary)
                                chunk_summaries.append(summary)
                    
                    # Save chunk summaries to cache
                    if chunk_summaries:
                        self._save_chunk_summaries_to_cache(video_id, chunk_summaries)
            else:
                # No video_id, process without caching
                summaries = []
                for i, chunk in enumerate(chunks):
                    if len(chunk.strip()) > 50:
                        logger.info(f"Processing chunk {i+1}/{len(chunks)}")
                        summary = self._summarize_single_chunk(chunk)
                        if summary and not summary.startswith("Summarization failed"):
                            summaries.append(summary)
            
            if summaries:
                # If we have multiple summaries, create a final summary
                if len(summaries) > 1:
                    combined_summary = " ".join(summaries)
                    # If combined is still too long, summarize the summaries
                    if len(combined_summary) > max_tokens * 4:  # rough char estimate
                        final_prompt = f"""Please create a comprehensive summary of these key points:

{combined_summary}

Provide a well-structured summary in Russian that captures the main topics and important details."""
                        
                        final_summary = self._summarize_single_chunk(final_prompt)
                        return final_summary
                    else:
                        return combined_summary
                else:
                    return summaries[0]
            else:
                return "Failed to generate summary for long text"
                
        except Exception as e:
            logger.error(f"Long text summarization failed: {e}")
            return f"Long text summarization failed: {str(e)}"
    
    def _create_summarization_prompt(self, text):
        """Create an effective summarization prompt"""
        return f"""Please create a comprehensive and well-structured summary of the following text. The text appears to be a transcript from a Russian-language video or podcast.

Instructions:
1. Summarize in Russian (the same language as the source)
2. Capture the main topics, key points, and important details
3. Organize the summary logically with clear structure
4. Keep the most interesting and relevant information
5. Make it readable and engaging
6. Aim for about 200-400 words

Text to summarize:
{text}

Summary:"""
    
    def get_service_info(self):
        """Get information about the service"""
        return {
            "service": "OpenRouter",
            "model": self.model,
            "initialized": self.is_initialized,
            "api_configured": bool(self.api_key and self.api_key != "your_openrouter_api_key_here")
        }
    
    def _clean_markdown_for_telegram(self, text):
        """Clean markdown formatting to avoid Telegram parsing errors"""
        try:
            import re
            
            # Remove problematic markdown syntax that causes Telegram errors
            # Keep basic formatting but remove complex structures
            
            # Remove complex markdown headers (### ## #)
            text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
            
            # Remove code blocks completely
            text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
            text = re.sub(r'`[^`]*`', '', text)
            
            # Remove markdown tables
            text = re.sub(r'\|[^\n]*\|', '', text)
            
            # Remove markdown links but keep the text
            text = re.sub(r'\[([^\]]*)\]\([^\)]*\)', r'\1', text)
            
            # Remove bullet points with special characters and normalize
            text = re.sub(r'^[\s]*[-*+•▪▫◦‣⁃]\s*', '• ', text, flags=re.MULTILINE)
            
            # Remove numbered lists with special formatting
            text = re.sub(r'^[\s]*\d+\.\s*\*\*([^*]*)\*\*', r'\1:', text, flags=re.MULTILINE)
            
            # Convert bold markdown to simple text (avoid ** issues)
            text = re.sub(r'\*\*([^*]*)\*\*', r'\1', text)
            text = re.sub(r'\*([^*]*)\*', r'\1', text)
            
            # Remove underscores that could be interpreted as markdown
            text = re.sub(r'_([^_]*)_', r'\1', text)
            
            # Remove any remaining problematic characters that Telegram might not like
            # Keep only safe characters for Telegram
            text = re.sub(r'[^\w\s\.\,\!\?\:\;\(\)\[\]\/\-\+\=\@\#\$\%\&\*\^\~\`\"\'•№]', ' ', text)
            
            # Clean up multiple newlines
            text = re.sub(r'\n{3,}', '\n\n', text)
            
            # Clean up extra spaces
            text = re.sub(r' {2,}', ' ', text)
            
            # Remove leading/trailing whitespace from each line
            lines = [line.strip() for line in text.split('\n')]
            text = '\n'.join(lines)
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error cleaning markdown: {e}")
            return text

    def _get_cache_paths(self, video_id):
        """Get cache file paths for a video"""
        cache_dir = "./cache"
        os.makedirs(cache_dir, exist_ok=True)
        
        return {
            'summary': os.path.join(cache_dir, f"{video_id}.summary.txt"),
            'chunks_dir': os.path.join(cache_dir, f"{video_id}_chunks"),
            'chunk_summaries': os.path.join(cache_dir, f"{video_id}.chunk_summaries.json")
        }

    def _save_to_cache(self, video_id, summary):
        """Save summary to cache"""
        try:
            cache_paths = self._get_cache_paths(video_id)
            
            # Save summary
            with open(cache_paths['summary'], 'w', encoding='utf-8') as f:
                f.write(summary)
            
            logger.info(f"✅ Cached summary for {video_id}")
            
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")

    def _save_chunk_summaries_to_cache(self, video_id, chunk_summaries):
        """Save chunk summaries to cache"""
        try:
            cache_paths = self._get_cache_paths(video_id)
            
            with open(cache_paths['chunk_summaries'], 'w', encoding='utf-8') as f:
                json.dump(chunk_summaries, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Cached {len(chunk_summaries)} chunk summaries for {video_id}")
            
        except Exception as e:
            logger.error(f"Failed to save chunk summaries cache: {e}")

    def _load_chunk_summaries_from_cache(self, video_id):
        """Load chunk summaries from cache if they exist"""
        try:
            cache_paths = self._get_cache_paths(video_id)
            
            if os.path.exists(cache_paths['chunk_summaries']):
                with open(cache_paths['chunk_summaries'], 'r', encoding='utf-8') as f:
                    chunk_summaries = json.load(f)
                
                if chunk_summaries:
                    logger.info(f"✅ Loaded {len(chunk_summaries)} chunk summaries from cache for {video_id}")
                    return chunk_summaries
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load chunk summaries from cache: {e}")
            return None

    def get_cached_chunk_summaries(self, video_id):
        """Get cached chunk summaries for a video (public method)"""
        return self._load_chunk_summaries_from_cache(video_id)

    def _load_from_cache(self, video_id):
        """Load summary from cache if it exists"""
        try:
            cache_paths = self._get_cache_paths(video_id)
            
            if os.path.exists(cache_paths['summary']):
                with open(cache_paths['summary'], 'r', encoding='utf-8') as f:
                    summary = f.read().strip()
                
                if summary:
                    logger.info(f"✅ Loaded summary from cache for {video_id}")
                    return summary
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to load from cache: {e}")
            return None
