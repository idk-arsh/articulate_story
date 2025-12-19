"""
GPT Translator using OpenRouter API
Handles translation calls with rate limiting and retries
Uses direct HTTP requests for better compatibility
"""

import os
import time
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

from app.translation.tag_manager import TagManager

# Load environment variables
load_dotenv()


class GPTTranslator:
    """Handles translation using OpenRouter API"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        """
        Initialize translator with OpenRouter credentials.
        
        Args:
            api_key: OpenRouter API key (or from env OPENROUTER_API_KEY)
            model: Model to use (or from env OPENAI_MODEL)
            base_url: API base URL (defaults to OpenRouter)
        """
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.model = model or os.getenv('OPENAI_MODEL', 'anthropic/claude-3.5-sonnet')
        self.base_url = base_url or os.getenv('OPENAI_API_BASE', 'https://openrouter.ai/api/v1')
        
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key not found. Set OPENROUTER_API_KEY in .env file "
                "or pass api_key parameter"
            )
        
        # Prepare headers for API requests
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.getenv('OPENROUTER_SITE_URL', 'http://localhost:8501'),
            "X-Title": os.getenv('OPENROUTER_SITE_NAME', 'Storyline Translator'),
        }
        
        self.tag_manager = TagManager()
        
        # Rate limiting
        self.max_rpm = int(os.getenv('MAX_REQUESTS_PER_MINUTE', 20))
        self.request_times = []
        
        # Stats
        self.total_tokens_used = 0
        self.total_requests = 0
    
    def translate_segment(
        self,
        text: str,
        target_language: str,
        source_language: str = "English",
        glossary: Optional[Dict[str, str]] = None,
        tone: str = "Professional",
        context: str = ""
    ) -> Dict:
        """
        Translate a single text segment.
        
        Args:
            text: Text to translate
            target_language: Target language name
            source_language: Source language name
            glossary: Dictionary of terms to enforce
            tone: Translation tone (Professional, Formal, Informal)
            context: Additional context about the text
            
        Returns:
            Dictionary with:
                - translated_text: The translation
                - protected_text: Text with tags protected (for debugging)
                - mapping: Tag protection mapping
                - tokens_used: Number of tokens consumed
                - model: Model used
        """
        # Protect tags
        protected_text, mapping = self.tag_manager.protect_tags(text)
        
        # Build prompt
        prompt = self._build_prompt(
            protected_text,
            target_language,
            source_language,
            glossary,
            tone,
            context
        )
        
        # Translate with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Rate limiting
                self._wait_for_rate_limit()
                
                # Prepare API request
                payload = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a professional translator specializing in e-learning content."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000
                }
                
                # Make API call using requests
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=60
                )
                
                # Check for errors
                response.raise_for_status()
                
                # Parse response
                data = response.json()
                
                # Extract translation
                translated_protected = data['choices'][0]['message']['content'].strip()
                
                # Restore tags
                translated_text = self.tag_manager.restore_tags(translated_protected, mapping)
                
                # Track usage
                tokens_used = data.get('usage', {}).get('total_tokens', 0)
                self.total_tokens_used += tokens_used
                self.total_requests += 1
                
                return {
                    'translated_text': translated_text,
                    'protected_text': protected_text,
                    'mapping': mapping,
                    'tokens_used': tokens_used,
                    'model': self.model,
                    'success': True
                }
                
            except requests.exceptions.HTTPError as e:
                error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"Translation attempt {attempt + 1} failed: {error_msg}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"Translation failed after {max_retries} attempts: {error_msg}")
                    return {
                        'translated_text': text,
                        'protected_text': protected_text,
                        'mapping': mapping,
                        'tokens_used': 0,
                        'model': self.model,
                        'success': False,
                        'error': error_msg
                    }
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"Translation attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"Translation failed after {max_retries} attempts: {e}")
                    return {
                        'translated_text': text,
                        'protected_text': protected_text,
                        'mapping': mapping,
                        'tokens_used': 0,
                        'model': self.model,
                        'success': False,
                        'error': str(e)
                    }
    
    def translate_segments(
        self,
        segments: List,
        target_language: str,
        source_language: str = "English",
        glossary: Optional[Dict[str, str]] = None,
        tone: str = "Professional",
        progress_callback: Optional[callable] = None
    ) -> List[Dict]:
        """
        Translate multiple segments.
        
        Args:
            segments: List of Segment objects
            target_language: Target language
            source_language: Source language
            glossary: Glossary dictionary
            tone: Translation tone
            progress_callback: Optional callback(current, total) for progress updates
            
        Returns:
            List of translation results
        """
        results = []
        total = len(segments)
        
        for i, segment in enumerate(segments, 1):
            # Translate
            result = self.translate_segment(
                text=segment.source_text,
                target_language=target_language,
                source_language=source_language,
                glossary=glossary,
                tone=tone,
                context=segment.context
            )
            
            # Update segment
            segment.target_text = result['translated_text']
            
            # Store full result
            result['segment_id'] = segment.id
            results.append(result)
            
            # Progress callback
            if progress_callback:
                progress_callback(i, total)
        
        return results
    
    def _build_prompt(
        self,
        text: str,
        target_language: str,
        source_language: str,
        glossary: Optional[Dict[str, str]],
        tone: str,
        context: str
    ) -> str:
        """Build the translation prompt"""
        
        prompt_parts = [
            f"Translate the following {source_language} text to {target_language}.",
            "",
        ]
        
        # Add tone instructions
        tone_instructions = {
            "Professional": "Use professional, businesslike language appropriate for corporate training.",
            "Formal": "Use formal, polite language. Use formal pronouns (e.g., 'usted' in Spanish, 'vous' in French).",
            "Informal": "Use casual, conversational language. Use informal pronouns (e.g., 'tú' in Spanish, 'tu' in French)."
        }
        
        if tone in tone_instructions:
            prompt_parts.append(f"**Tone:** {tone_instructions[tone]}")
        
        # Add tag protection instructions
        prompt_parts.append("")
        prompt_parts.append(self.tag_manager.get_prompt_instructions())
        
        # Add glossary if provided
        if glossary and len(glossary) > 0:
            prompt_parts.append("")
            prompt_parts.append("**Glossary (use these exact translations):**")
            for source_term, target_term in glossary.items():
                if target_term == source_term or target_term.lower() == "do not translate":
                    prompt_parts.append(f"- '{source_term}' → Keep as '{source_term}' (do not translate)")
                else:
                    prompt_parts.append(f"- '{source_term}' → '{target_term}'")
        
        # Add context if provided
        if context:
            prompt_parts.append("")
            prompt_parts.append(f"**Context:** {context}")
        
        # Add the text to translate
        prompt_parts.append("")
        prompt_parts.append("**Text to translate:**")
        prompt_parts.append(text)
        prompt_parts.append("")
        prompt_parts.append("**Your translation (ONLY the translated text, no explanations):**")
        
        return "\n".join(prompt_parts)
    
    def _wait_for_rate_limit(self):
        """Implement simple rate limiting"""
        now = time.time()
        
        # Remove requests older than 1 minute
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        # If at limit, wait
        if len(self.request_times) >= self.max_rpm:
            sleep_time = 60 - (now - self.request_times[0])
            if sleep_time > 0:
                print(f"Rate limit reached. Waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)
                # Refresh the list
                now = time.time()
                self.request_times = [t for t in self.request_times if now - t < 60]
        
        # Add this request
        self.request_times.append(now)
    
    def get_stats(self) -> Dict:
        """Get usage statistics"""
        return {
            'total_requests': self.total_requests,
            'total_tokens': self.total_tokens_used,
            'model': self.model,
            'estimated_cost': self._estimate_cost()
        }
    
    def _estimate_cost(self) -> str:
        """Estimate cost based on tokens used (approximate)"""
        # These are rough estimates - actual costs vary by model
        cost_per_1k = {
            'anthropic/claude-3.5-sonnet': 0.003,
            'openai/gpt-4-turbo': 0.01,
            'openai/gpt-3.5-turbo': 0.0015,
            'google/gemini-pro': 0.00025,
        }
        
        rate = cost_per_1k.get(self.model, 0.002)  # Default estimate
        cost = (self.total_tokens_used / 1000) * rate
        
        return f"${cost:.4f} (estimated)"


# Convenience function
def translate_text(
    text: str,
    target_language: str,
    **kwargs
) -> str:
    """Quick translation function"""
    translator = GPTTranslator()
    result = translator.translate_segment(text, target_language, **kwargs)
    return result['translated_text']