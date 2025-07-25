import requests
from huggingface_hub import InferenceClient
from transformers import pipeline
from config import HF_TOKEN


class SummarizationService:
    def __init__(self):
        self.hf_token = HF_TOKEN
        self.client = None
        self.summarizer = None
        self._init_client()
    
    def _init_client(self):
        """Initialize the InferenceClient"""
        try:
            if self.hf_token:
                self.client = InferenceClient(
#                    model="facebook/bart-large-cnn",
                    model="IlyaGusev/rut5_base_sum_gazeta",
                    token=self.hf_token
                )
                print("✅ HuggingFace InferenceClient initialized")
            else:
                print("❌ HF_TOKEN not found, falling back to local model")
                self._init_local_summarizer()
        except Exception as e:
            print(f"Failed to initialize InferenceClient: {e}")
            self._init_local_summarizer()
    
    def _init_local_summarizer(self):
        """Initialize the local summarization pipeline as fallback"""
        try:
            self.summarizer = pipeline(
                "summarization",
                model="IlyaGusev/rut5_base_sum_gazeta",
                token=self.hf_token
            )
            print("✅ Local summarizer initialized as fallback")
        except Exception as e:
            print(f"Failed to initialize local summarizer: {e}")
            self.summarizer = None
    
    def summarize_text(self, text):
        """Summarize the given text"""
        if not text or len(text.strip()) < 50:
            return "Text too short to summarize."
        
        try:
            # Try InferenceClient first
            if self.client:
                return self._summarize_with_client(text)
            # Fall back to local summarization
            elif self.summarizer:
                return self._summarize_local(text)
            else:
                return self._summarize_api(text)
        except Exception as e:
            return f"Summarization failed: {str(e)}"
    
    def _summarize_with_client(self, text):
        """Summarize using HuggingFace InferenceClient"""
        try:
            # Split text into chunks if too long (InferenceClient has limits)
            max_length = 1024
            if len(text) > max_length:
                chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
                summaries = []
                
                for chunk in chunks:
                    if len(chunk.strip()) > 50:
                        result = self.client.summarization(chunk)
                        # Handle SummarizationOutput object
                        if hasattr(result, 'summary_text'):
                            summaries.append(result.summary_text)
                        elif isinstance(result, list) and len(result) > 0:
                            summary_text = result[0].get('summary_text', str(result[0]))
                            summaries.append(summary_text)
                        elif isinstance(result, dict) and 'summary_text' in result:
                            summaries.append(result['summary_text'])
                        else:
                            summaries.append(str(result))
                
                return " ".join(summaries)
            else:
                result = self.client.summarization(text)
                
                # Handle SummarizationOutput object (most common case)
                if hasattr(result, 'summary_text'):
                    return result.summary_text
                elif isinstance(result, list) and len(result) > 0:
                    return result[0].get('summary_text', str(result[0]))
                elif isinstance(result, dict) and 'summary_text' in result:
                    return result['summary_text']
                elif isinstance(result, str):
                    return result
                else:
                    return str(result)
                    
        except Exception as e:
            print(f"InferenceClient failed: {e}")
            # Fall back to local summarization
            if self.summarizer:
                return self._summarize_local(text)
            else:
                raise Exception(f"InferenceClient summarization failed: {str(e)}")
    
    def _summarize_local(self, text):
        """Summarize using local transformers pipeline"""
        try:
            # Split text into chunks if too long
            max_length = 1024
            if len(text) > max_length:
                chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
                summaries = []
                
                for chunk in chunks:
                    if len(chunk.strip()) > 50:
                        result = self.summarizer(
                            chunk,
                            max_length=150,
                            min_length=30,
                            do_sample=False
                        )
                        summaries.append(result[0]['summary_text'])
                
                return " ".join(summaries)
            else:
                result = self.summarizer(
                    text,
                    max_length=200,
                    min_length=50,
                    do_sample=False
                )
                return result[0]['summary_text']
        except Exception as e:
            raise Exception(f"Local summarization failed: {str(e)}")
    
    def _summarize_api(self, text):
        """Summarize using Hugging Face API"""
        try:
            api_url = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
            headers = {"Authorization": f"Bearer {self.hf_token}"}
            
            # Split text if too long
            max_length = 1024
            if len(text) > max_length:
                text = text[:max_length]
            
            payload = {"inputs": text}
            response = requests.post(api_url, headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get('summary_text', 'No summary generated')
                else:
                    return 'No summary generated'
            else:
                raise Exception(f"API request failed: {response.status_code}")
                
        except Exception as e:
            raise Exception(f"API summarization failed: {str(e)}")
