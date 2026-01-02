"""
GPT Translator using OpenRouter API
NOW WITH BATCH TRANSLATION SUPPORT! (Fixed & Cleaned)
"""

import os
import time
import json
import requests
import re
from typing import List, Dict, Optional
from dotenv import load_dotenv

from app.translation.tag_manager import TagManager

load_dotenv()


class GPTTranslator:
    """Handles translation using OpenRouter API"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        self.model = model or os.getenv('OPENAI_MODEL', 'anthropic/claude-3.5-sonnet')
        self.base_url = base_url or os.getenv('OPENAI_API_BASE', 'https://openrouter.ai/api/v1')
        
        if not self.api_key:
            raise ValueError(
                "OpenRouter API key not found. Set OPENROUTER_API_KEY in .env file "
                "or pass api_key parameter"
            )
        
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
        """Translate a single text segment."""
        
        # Extract and save leading number
        match = re.match(r'^(\d+)\s*', text)
        if match:
            leading_num = match.group(0)
            text_without_num = text[len(leading_num):]
        else:
            leading_num = ""
            text_without_num = text
        
        protected_text, mapping = self.tag_manager.protect_tags(text_without_num)
        system_prompt = self._build_system_prompt(tone)
        user_prompt = self._build_user_prompt(
            protected_text, target_language, source_language, glossary, context
        )
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit()
                
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000
                }
                
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=60
                )
                
                response.raise_for_status()
                data = response.json()
                
                translated_protected = data['choices'][0]['message']['content'].strip()
                translated_protected = self._clean_translation_output(translated_protected)
                translated_text = self.tag_manager.restore_tags(translated_protected, mapping)
                
                # Re-add leading number
                if leading_num:
                    translated_text = leading_num + translated_text
                
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
    
    # ========== BATCH TRANSLATION ==========
    
    def translate_segments_batch(
        self,
        segments: List,
        target_language: str,
        source_language: str = "English",
        glossary: Optional[Dict[str, str]] = None,
        tone: str = "Professional",
        batch_size: int = 10,
        progress_callback: Optional[callable] = None
    ) -> List[Dict]:
        """
        Translate multiple segments in batches (much faster!)
        """
        
        results = []
        total = len(segments)
        total_batches = (total + batch_size - 1) // batch_size
        
        print(f"\nBatch translation: {total} segments in {total_batches} batches of {batch_size}")
        
        for batch_idx in range(0, total, batch_size):
            batch = segments[batch_idx:batch_idx + batch_size]
            batch_num = (batch_idx // batch_size) + 1
            
            print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} segments)...")
            
            try:
                batch_results = self._translate_batch(
                    batch, target_language, source_language, glossary, tone
                )
                
                results.extend(batch_results)
                
                if progress_callback and batch_num % 2 == 0:
                    current = min(batch_idx + batch_size, total)
                    progress_callback(current, total)
                
                print(f"Batch {batch_num} completed!")
                
            except Exception as e:
                print(f"Batch {batch_num} failed: {e}")
                
                for segment in batch:
                    segment.target_text = segment.source_text
                    segment.translation = segment.source_text
                    segment_id = getattr(segment, 'id', getattr(segment, 'id_text', 'unknown'))
                    results.append({
                        'segment_id': segment_id,
                        'translated_text': segment.source_text,
                        'success': False,
                        'error': str(e)
                    })
        
        return results
    
    def _translate_batch(
        self,
        batch: List,
        target_language: str,
        source_language: str,
        glossary: Optional[Dict[str, str]],
        tone: str
    ) -> List[Dict]:
        """Translate a batch of segments in one API call"""
        
        # Protect tags and preserve leading numbers
        protected_batch = []
        mappings = []
        leading_numbers = []
        
        for segment in batch:
            # Extract leading number
            match = re.match(r'^(\d+)\s*', segment.source_text)
            if match:
                leading_num = match.group(0)
                text_without_num = segment.source_text[len(leading_num):]
                leading_numbers.append(leading_num)
            else:
                leading_num = ""
                text_without_num = segment.source_text
                leading_numbers.append("")
            
            # Protect tags
            protected_text, mapping = self.tag_manager.protect_tags(text_without_num)
            protected_batch.append(protected_text)
            mappings.append(mapping)
        
        # Build prompts
        system_prompt = self._build_system_prompt(tone)
        user_prompt = self._build_batch_user_prompt(
            protected_batch, target_language, source_language, glossary
        )
        
        # API call
        self._wait_for_rate_limit()
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 4000
        }
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self.headers,
            json=payload,
            timeout=90
        )
        
        response.raise_for_status()
        data = response.json()
        
        # Parse response
        content = data['choices'][0]['message']['content'].strip()
        translations = self._parse_batch_response(content, len(batch))
        
        # Restore tags and re-add leading numbers
        results = []
        for i, segment in enumerate(batch):
            if i < len(translations):
                translated_text = self.tag_manager.restore_tags(translations[i], mappings[i])
                
                if leading_numbers[i]:
                    translated_text = leading_numbers[i] + translated_text
                
                segment.target_text = translated_text
                segment.translation = translated_text
                
                segment_id = getattr(segment, 'id', getattr(segment, 'id_text', f'batch_seg_{i}'))
                results.append({
                    'segment_id': segment_id,
                    'translated_text': translated_text,
                    'success': True
                })
            else:
                segment.target_text = segment.source_text
                segment.translation = segment.source_text
                
                segment_id = getattr(segment, 'id', getattr(segment, 'id_text', f'batch_seg_{i}'))
                results.append({
                    'segment_id': segment_id,
                    'translated_text': segment.source_text,
                    'success': False,
                    'error': 'Translation missing in batch response'
                })
        
        # Update stats
        tokens_used = data.get('usage', {}).get('total_tokens', 0)
        self.total_tokens_used += tokens_used
        self.total_requests += 1
        
        return results
    
    def _build_batch_user_prompt(
        self,
        texts: List[str],
        target_language: str,
        source_language: str,
        glossary: Optional[Dict[str, str]]
    ) -> str:
        """Build prompt for batch translation"""
        
        prompt_parts = []
        
        if glossary and len(glossary) > 0:
            prompt_parts.append("Use these terms:")
            for source_term, target_term in glossary.items():
                if target_term == source_term or target_term.lower() == "do not translate":
                    prompt_parts.append(f"  • '{source_term}' → keep as '{source_term}'")
                else:
                    prompt_parts.append(f"  • '{source_term}' → '{target_term}'")
            prompt_parts.append("")
        
        prompt_parts.append(f"Translate these {len(texts)} text segments from {source_language} to {target_language}.")
        prompt_parts.append("")
        prompt_parts.append("IMPORTANT RULES:")
        prompt_parts.append("1. Return ONLY a JSON array with exactly " + str(len(texts)) + " translations")
        prompt_parts.append("2. Preserve ALL numbers, formatting, and structure from the original text")
        prompt_parts.append("3. Format: [\"translation1\", \"translation2\", ...]")
        prompt_parts.append("")
        prompt_parts.append("Text segments to translate:")
        prompt_parts.append("")
        
        for i, text in enumerate(texts, 1):
            prompt_parts.append(f"=== Segment {i} ===")
            prompt_parts.append(text)
            prompt_parts.append("")
        
        return "\n".join(prompt_parts)
    
    def _parse_batch_response(self, content: str, expected_count: int) -> List[str]:
        """Parse batch translation JSON response"""
        
        content = content.strip()
        if content.startswith('```'):
            lines = content.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            content = '\n'.join(lines)
        
        try:
            translations = json.loads(content)
            if not isinstance(translations, list):
                raise ValueError("Response is not a JSON array")
            
            cleaned_translations = [str(t).strip() for t in translations]
            
            if len(cleaned_translations) != expected_count:
                print(f"Warning: Expected {expected_count} translations, got {len(cleaned_translations)}")
            
            return cleaned_translations
            
        except json.JSONDecodeError as e:
            print(f"JSON parse failed: {e}")
            print(f"Response: {content[:300]}...")
            
            matches = re.findall(r'"([^"]*)"', content)
            if len(matches) >= expected_count:
                return matches[:expected_count]
            
            print("Using fallback - returning empty strings")
            return ["" for _ in range(expected_count)]
    
    # ========== END OF BATCH ==========
    
    def translate_segments(
        self,
        segments: List,
        target_language: str,
        source_language: str = "English",
        glossary: Optional[Dict[str, str]] = None,
        tone: str = "Professional",
        progress_callback: Optional[callable] = None,
        use_batch: bool = False,
        batch_size: int = 10
    ) -> List[Dict]:
        if use_batch:
            return self.translate_segments_batch(
                segments, target_language, source_language,
                glossary, tone, batch_size, progress_callback
            )
        
        results = []
        total = len(segments)
        
        for i, segment in enumerate(segments, 1):
            result = self.translate_segment(
                text=segment.source_text,
                target_language=target_language,
                source_language=source_language,
                glossary=glossary,
                tone=tone,
                context=getattr(segment, 'context', '')
            )
            
            segment.target_text = result['translated_text']
            
            segment_id = getattr(segment, 'id', getattr(segment, 'id_text', f'segment_{i}'))
            result['segment_id'] = segment_id
            results.append(result)
            
            if progress_callback:
                progress_callback(i, total)
        
        return results
    
    def _build_system_prompt(self, tone: str) -> str:
        tone_instructions = {
            "Professional": "Use professional, businesslike language appropriate for corporate training.",
            "Formal": "Use formal, polite language. Use formal pronouns (e.g., 'usted' in Spanish, 'vous' in French).",
            "Informal": "Use casual, conversational language. Use informal pronouns (e.g., 'tú' in Spanish, 'tu' in French)."
        }
        
        tone_instruction = tone_instructions.get(tone, tone_instructions["Professional"])
        
        return f"""You are a professional translator specializing in e-learning content.

CRITICAL RULES:
1. Output ONLY the translated text - no explanations, no notes, no preambles
2. Never include translation instructions in your output
3. Preserve ALL placeholder tokens exactly as they appear (e.g., [[TAG_0_XLIFF_TAG]])
4. Do not translate or modify text inside double square brackets [[...]]
5. Keep placeholders in approximately the same position in the sentence

Translation Style: {tone_instruction}"""

    def _build_user_prompt(
        self,
        text: str,
        target_language: str,
        source_language: str,
        glossary: Optional[Dict[str, str]],
        context: str
    ) -> str:
        prompt_parts = []
        
        if glossary and len(glossary) > 0:
            prompt_parts.append("Use these terms:")
            for source_term, target_term in glossary.items():
                if target_term == source_term or target_term.lower() == "do not translate":
                    prompt_parts.append(f"  • '{source_term}' → keep as '{source_term}'")
                else:
                    prompt_parts.append(f"  • '{source_term}' → '{target_term}'")
            prompt_parts.append("")
        
        if context:
            prompt_parts.append(f"Context: {context}")
            prompt_parts.append("")
        
        prompt_parts.append(f"Translate from {source_language} to {target_language}:")
        prompt_parts.append("")
        prompt_parts.append(text)
        
        return "\n".join(prompt_parts)
    
    def _clean_translation_output(self, text: str) -> str:
        cleanup_patterns = [
            "**CRITICAL RULES", "**Reglas críticas", "**REGLAS CRÍTICAS",
            "**Translated text:**", "**Texto traducido:**",
            "Here is the translation:", "Aquí está la traducción:",
        ]
        
        for pattern in cleanup_patterns:
            if pattern.lower() in text.lower()[:200]:
                split_markers = [
                    "**Translated text:**", "**Texto traducido:**",
                    "Translation:", "Traducción:",
                ]
                
                for marker in split_markers:
                    if marker in text:
                        parts = text.split(marker, 1)
                        if len(parts) > 1:
                            text = parts[1].strip()
                            break
                
                if any(p.lower() in text.lower() for p in ["critical rules", "reglas críticas"]):
                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                    for line in reversed(lines):
                        if not any(marker in line.lower() for marker in ["rule", "regla", "ejemplo", "example"]):
                            text = line
                            break
        
        return text.strip()
    
    def _wait_for_rate_limit(self):
        now = time.time()
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        if len(self.request_times) >= self.max_rpm:
            sleep_time = 60 - (now - self.request_times[0])
            if sleep_time > 0:
                print(f"Rate limit reached. Waiting {sleep_time:.1f}s...")
                time.sleep(sleep_time)
                now = time.time()
                self.request_times = [t for t in self.request_times if now - t < 60]
        
        self.request_times.append(now)
    
    def get_stats(self) -> Dict:
        return {
            'total_requests': self.total_requests,
            'total_tokens': self.total_tokens_used,
            'model': self.model,
            'estimated_cost': self._estimate_cost()
        }
    
    def _estimate_cost(self) -> str:
        cost_per_1k = {
            'anthropic/claude-3.5-sonnet': 0.003,
            'openai/gpt-4-turbo': 0.01,
            'openai/gpt-3.5-turbo': 0.0015,
            'google/gemini-pro': 0.00025,
        }
        
        rate = cost_per_1k.get(self.model, 0.002)
        cost = (self.total_tokens_used / 1000) * rate
        
        return f"${cost:.4f} (estimated)"