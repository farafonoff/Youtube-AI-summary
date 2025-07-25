from telegraph import Telegraph
import logging
import requests
from config import TELEGRAPH_TOKEN

logger = logging.getLogger(__name__)


class TelegraphService:
    def __init__(self):
        try:
            self.telegraph = Telegraph()
            self.token = TELEGRAPH_TOKEN
            self.is_initialized = False
            
            if self.token:
                self._initialize_with_token()
            else:
                logger.warning("No Telegraph token found in environment. Telegraph service will be disabled.")
                self.telegraph = None
                
        except Exception as e:
            logger.warning(f"Telegraph library initialization failed: {e}")
            self.telegraph = None
            self.is_initialized = False
    
    def _initialize_with_token(self):
        """Initialize Telegraph with existing token"""
        try:
            if self.telegraph and self.token:
                # Initialize Telegraph with the token
                self.telegraph = Telegraph(access_token=self.token)
                self.is_initialized = True
                logger.info("✅ Telegraph service initialized with token")
            else:
                logger.error("Telegraph initialization failed: missing token")
                self.is_initialized = False
        except Exception as e:
            logger.error(f"Failed to initialize Telegraph with token: {e}")
            self.is_initialized = False
    
    def _ensure_initialized(self):
        """Ensure Telegraph is initialized"""
        if self.telegraph is None:
            logger.error("Telegraph library not available")
            return False
            
        return self.is_initialized
    
    def create_page(self, title, content, video_url=None):
        """Create a Telegraph page with the given content"""
        if not self._ensure_initialized():
            logger.error("Telegraph service could not be initialized")
            return None
            
        try:
            # Prepare content for Telegraph (needs to be HTML-like)
            formatted_content = self._format_content(content, video_url)
            
            # Limit content length (Telegraph has limits)
            if len(formatted_content) > 60000:  # Telegraph limit is around 64KB
                formatted_content = formatted_content[:60000] + "... [Content truncated]"
            
            # Create the page
            response = self.telegraph.create_page(
                title=title[:256],  # Telegraph title limit
                html_content=formatted_content,
            )
            
            # Check different response formats
            if response and 'path' in response:
                page_url = f"https://telegra.ph/{response['path']}"
                logger.info(f"✅ Telegraph page created: {page_url}")
                return page_url
            elif response and 'result' in response and 'path' in response['result']:
                page_url = f"https://telegra.ph/{response['result']['path']}"
                logger.info(f"✅ Telegraph page created: {page_url}")
                return page_url
            else:
                logger.error(f"Telegraph page creation failed: {response}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to create Telegraph page: {e}")
            return None
    
    def _format_content(self, content, video_url=None):
        """Format content for Telegraph"""
        try:
            # Start with video link if provided
            html_content = ""
            
            if video_url:
                html_content += f'<p><strong>🎥 Original Video:</strong> <a href="{video_url}">{video_url}</a></p>\n\n'
            
            html_content += f'<p><strong>📝 Full Transcription:</strong></p>\n\n'
            
            # Split content into paragraphs and format
            paragraphs = content.split('\n')
            
            for paragraph in paragraphs:
                paragraph = paragraph.strip()
                if paragraph:
                    # Escape HTML characters
                    paragraph = paragraph.replace('&', '&amp;')
                    paragraph = paragraph.replace('<', '&lt;')
                    paragraph = paragraph.replace('>', '&gt;')
                    paragraph = paragraph.replace('"', '&quot;')
                    
                    html_content += f'<p>{paragraph}</p>\n'
            
            return html_content
            
        except Exception as e:
            logger.error(f"Failed to format content: {e}")
            return f"<p>{content}</p>"
