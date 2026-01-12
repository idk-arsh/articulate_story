"""
GPT Translator with DETAILED LOGGING and ANTI-MERGE PROTECTION
Prevents AI from merging segments together
"""

import os
import time
import json
import requests
import re
from typing import List, Dict, Optional
from dotenv import load_dotenv
import logging

from app.translation.tag_manager import TagManager

load_dotenv()

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GPTTranslator:
    """Handles translation using OpenRouter API with detailed logging"""
    
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
        
        logger.info(f"✓ Translator initialized")
        logger.info(f"  Model: {self.model}")
        logger.info(f"  Rate limit: {self.max_rpm} requests/min")
    
    # ========== BATCH TRANSLATION WITH ANTI-MERGE PROTECTION ==========
    
    def translate_segments_batch(
        self,
        segments: List,
        target_language: str,
        source_language: str = "English",
        glossary: Optional[Dict[str, str]] = None,
        tone: str = "Professional",
        batch_size: int = 70,  # REDUCED from 80 for better reliability
        progress_callback: Optional[callable] = None
    ) -> List[Dict]:
        """
        Translate multiple segments in batches with ANTI-MERGE PROTECTION
        """
        
        results = []
        total = len(segments)
        total_batches = (total + batch_size - 1) // batch_size
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("BATCH TRANSLATION STARTED")
        logger.info("=" * 70)
        logger.info(f"Total segments: {total}")
        logger.info(f"Batch size: {batch_size}")
        logger.info(f"Total batches: {total_batches}")
        logger.info(f"Source language: {source_language}")
        logger.info(f"Target language: {target_language}")
        logger.info(f"Tone: {tone}")
        if glossary:
            logger.info(f"Glossary terms: {len(glossary)}")
        logger.info("=" * 70)
        logger.info("")
        
        start_time = time.time()
        
        for batch_idx in range(0, total, batch_size):
            batch = segments[batch_idx:batch_idx + batch_size]
            batch_num = (batch_idx // batch_size) + 1
            
            logger.info("")
            logger.info("*" * 70)
            logger.info(f"BATCH {batch_num}/{total_batches} - Processing {len(batch)} segments")
            logger.info("*" * 70)
            
            try:
                batch_results = self._translate_batch_with_validation(
                    batch, batch_num, total_batches,
                    target_language, source_language, glossary, tone
                )
                
                results.extend(batch_results)
                
                if progress_callback:
                    progress_callback(batch_num, total_batches)
                
                logger.info(f"✓ Batch {batch_num}/{total_batches} completed successfully")
                
            except Exception as e:
                logger.error(f"✗ Batch {batch_num} FAILED: {e}")
                
                # Fill with fallback results
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
        
        elapsed = time.time() - start_time
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("BATCH TRANSLATION COMPLETED")
        logger.info("=" * 70)
        logger.info(f"Total time: {elapsed:.2f} seconds")
        logger.info(f"Speed: {total/elapsed:.1f} segments/second")
        logger.info(f"Total API calls: {self.total_requests}")
        logger.info(f"Total tokens used: {self.total_tokens_used:,}")
        logger.info(f"Average time per batch: {elapsed/total_batches:.1f}s")
        logger.info("=" * 70)
        logger.info("")
        
        return results
    
    def _translate_batch_with_validation(
        self,
        batch: List,
        batch_num: int,
        total_batches: int,
        target_language: str,
        source_language: str,
        glossary: Optional[Dict[str, str]],
        tone: str
    ) -> List[Dict]:
        """
        Translate a batch with VALIDATION and AUTO-RETRY on mismatch
        """
        
        logger.info("")
        logger.info("-" * 70)
        logger.info(f"BATCH {batch_num} - PREPARING DATA")
        logger.info("-" * 70)
        
        # Protect tags and preserve leading numbers
        protected_batch = []
        mappings = []
        leading_numbers = []
        segment_ids = []
        
        logger.info(f"Processing {len(batch)} segments for protection...")
        
        for i, segment in enumerate(batch):
            # Extract segment ID
            segment_id = getattr(segment, 'id', getattr(segment, 'id_text', f'seg_{i}'))
            segment_ids.append(segment_id)
            
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
            
            # Log each segment being prepared
            logger.info(f"  [{i+1}/{len(batch)}] ID:{segment_id} | Original: {segment.source_text[:60]}...")
            if mapping:
                logger.info(f"       → Tags protected: {len(mapping)} placeholders")
        
        # Build prompts with STRICT FORMATTING
        system_prompt = self._build_system_prompt_strict(tone)
        user_prompt = self._build_batch_user_prompt_strict(
            protected_batch, segment_ids, target_language, source_language, glossary
        )
        
        logger.info("")
        logger.info("-" * 70)
        logger.info(f"BATCH {batch_num} - SENDING TO AI")
        logger.info("-" * 70)
        logger.info(f"System prompt length: {len(system_prompt)} characters")
        logger.info(f"User prompt length: {len(user_prompt)} characters")
        
        # API call
        self._wait_for_rate_limit()
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 16000
        }
        
        logger.info(f"Sending API request to {self.model}...")
        api_start = time.time()
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=120
            )
            
            api_elapsed = time.time() - api_start
            logger.info(f"✓ API responded in {api_elapsed:.2f} seconds")
            
            response.raise_for_status()
            data = response.json()
            
            # Log what we received
            content = data['choices'][0]['message']['content'].strip()
            tokens_used = data.get('usage', {}).get('total_tokens', 0)
            
            logger.info("")
            logger.info("-" * 70)
            logger.info(f"BATCH {batch_num} - RECEIVED FROM AI")
            logger.info("-" * 70)
            logger.info(f"Response length: {len(content)} characters")
            logger.info(f"Total tokens: {tokens_used:,}")
            logger.info("")
            logger.info(">>> AI RESPONSE (first 1000 chars):")
            logger.info("-" * 70)
            logger.info(content[:1000])
            if len(content) > 1000:
                logger.info(f"... (+ {len(content) - 1000} more characters)")
            logger.info("-" * 70)
            
            # Parse response with VALIDATION
            logger.info("")
            logger.info(f"Parsing and validating response...")
            translations = self._parse_and_validate_batch(content, len(batch), segment_ids)
            
            # CRITICAL CHECK: Count mismatch detection
            if len(translations) != len(batch):
                logger.error("")
                logger.error("!" * 70)
                logger.error(f"CRITICAL: TRANSLATION COUNT MISMATCH!")
                logger.error(f"Expected: {len(batch)} segments")
                logger.error(f"Received: {len(translations)} translations")
                logger.error(f"Difference: {abs(len(translations) - len(batch))} segments")
                logger.error("!" * 70)
                logger.error("")
                
                # AUTO-RETRY with smaller batch size
                logger.warning("🔄 AUTO-RETRY: Splitting batch into individual segments...")
                return self._retry_batch_individually(
                    batch, batch_num, target_language, source_language, 
                    glossary, tone, protected_batch, mappings, leading_numbers, segment_ids
                )
            
            # If counts match, proceed with restoration
            logger.info(f"✓ Validation passed: {len(translations)} translations match {len(batch)} segments")
            
            # Restore tags and re-add leading numbers
            logger.info("")
            logger.info("-" * 70)
            logger.info(f"BATCH {batch_num} - RESTORING TAGS & APPLYING TRANSLATIONS")
            logger.info("-" * 70)
            
            results = []
            for i, segment in enumerate(batch):
                translated_text = self.tag_manager.restore_tags(translations[i], mappings[i])
                
                if leading_numbers[i]:
                    translated_text = leading_numbers[i] + translated_text
                
                segment.target_text = translated_text
                segment.translation = translated_text
                
                # Log each translation
                logger.info(f"  [{i+1}/{len(batch)}] ID:{segment_ids[i]}")
                logger.info(f"       Source: {segment.source_text[:60]}...")
                logger.info(f"       Target: {translated_text[:60]}...")
                logger.info(f"       ✓ Success")
                
                results.append({
                    'segment_id': segment_ids[i],
                    'translated_text': translated_text,
                    'success': True
                })
            
            # Update stats
            self.total_tokens_used += tokens_used
            self.total_requests += 1
            
            logger.info("")
            logger.info(f"Batch {batch_num} statistics:")
            logger.info(f"  - API time: {api_elapsed:.2f}s")
            logger.info(f"  - Tokens used: {tokens_used:,}")
            logger.info(f"  - Successful: {len(results)}/{len(batch)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Batch {batch_num} API call failed: {e}")
            logger.exception(e)
            raise
    
    def _retry_batch_individually(
        self,
        batch: List,
        batch_num: int,
        target_language: str,
        source_language: str,
        glossary: Optional[Dict[str, str]],
        tone: str,
        protected_batch: List[str],
        mappings: List[Dict],
        leading_numbers: List[str],
        segment_ids: List[str]
    ) -> List[Dict]:
        """
        Retry failed batch by translating each segment individually
        This prevents merge errors from affecting the entire batch
        """
        logger.warning("")
        logger.warning("=" * 70)
        logger.warning(f"INDIVIDUAL RETRY MODE - Batch {batch_num}")
        logger.warning("=" * 70)
        logger.warning(f"Translating {len(batch)} segments one-by-one to ensure accuracy")
        logger.warning("=" * 70)
        logger.warning("")
        
        results = []
        
        for i, segment in enumerate(batch):
            logger.info(f"  Retry [{i+1}/{len(batch)}] ID:{segment_ids[i]}...")
            
            try:
                # Translate single segment
                result = self.translate_segment(
                    text=segment.source_text,
                    target_language=target_language,
                    source_language=source_language,
                    glossary=glossary,
                    tone=tone,
                    context=""
                )
                
                segment.target_text = result['translated_text']
                segment.translation = result['translated_text']
                
                logger.info(f"       ✓ Success: {result['translated_text'][:60]}...")
                
                results.append({
                    'segment_id': segment_ids[i],
                    'translated_text': result['translated_text'],
                    'success': True
                })
                
            except Exception as e:
                logger.error(f"       ✗ Failed: {e}")
                
                # Fallback to original text
                segment.target_text = segment.source_text
                segment.translation = segment.source_text
                
                results.append({
                    'segment_id': segment_ids[i],
                    'translated_text': segment.source_text,
                    'success': False,
                    'error': str(e)
                })
        
        logger.warning("")
        logger.warning(f"Individual retry completed: {sum(1 for r in results if r['success'])}/{len(results)} successful")
        logger.warning("")
        
        return results
    
    def _build_system_prompt_strict(self, tone: str) -> str:
        """Build STRICT system prompt that prevents merging"""
        tone_instructions = {
            "Professional": "Use professional, businesslike language appropriate for corporate training.",
            "Formal": "Use formal, polite language. Use formal pronouns (e.g., 'usted' in Spanish, 'vous' in French).",
            "Informal": "Use casual, conversational language. Use informal pronouns (e.g., 'tú' in Spanish, 'tu' in French)."
        }
        
        tone_instruction = tone_instructions.get(tone, tone_instructions["Professional"])
        
        return f"""You are a professional translator specializing in e-learning content.

CRITICAL RULES - FOLLOW EXACTLY:
1. You will receive segments numbered with IDs like [ABC123]
2. Translate EACH segment SEPARATELY - DO NOT merge segments
3. Return EXACTLY one translation per segment - no more, no less
4. Preserve ALL [[TAG_X_...]] placeholders exactly as-is
5. Output ONLY a JSON array with no explanations
6. Each array element corresponds to ONE segment in order

VERY IMPORTANT - EMPTY / N/A SEGMENTS:
- If a segment contains only "N/A" (case insensitive) → return an **empty string** ""
- If a segment is completely empty ("") → return an **empty string** ""
- Do NOT return "N/A", "empty", "[EMPTY]" or any placeholder unless explicitly instructed

FORBIDDEN:
- Merging two segments into one translation
- Skipping segments
- Adding extra translations
- Combining content from multiple segments

Style: {tone_instruction}

Output format: ["translation1", "translation2", "translation3", ...]"""
    
    def _build_batch_user_prompt_strict(
        self,
        texts: List[str],
        segment_ids: List[str],
        target_language: str,
        source_language: str,
        glossary: Optional[Dict[str, str]]
    ) -> str:
        """Build STRICT batch prompt with clear segment boundaries"""
        
        prompt_parts = []
        
        # Glossary
        if glossary and len(glossary) > 0:
            prompt_parts.append("GLOSSARY:")
            for source_term, target_term in glossary.items():
                if target_term == source_term or target_term.lower() == "do not translate":
                    prompt_parts.append(f"  '{source_term}' → keep unchanged")
                else:
                    prompt_parts.append(f"  '{source_term}' → '{target_term}'")
            prompt_parts.append("")
        
        # Clear instructions
        prompt_parts.append(f"Translate exactly {len(texts)} segments from {source_language} to {target_language}.")
        prompt_parts.append("")
        prompt_parts.append("STRICT RULES:")
        prompt_parts.append(f"1. Return ONLY a JSON array with EXACTLY {len(texts)} strings")
        prompt_parts.append("2. Each translation must be INDEPENDENT - do NOT merge segments")
        prompt_parts.append("3. Preserve ALL [[TAG_X_...]] placeholders exactly")
        prompt_parts.append("4. Preserve ALL numbers and formatting")
        prompt_parts.append("5. Even if a segment seems incomplete, translate it AS-IS")
        prompt_parts.append(f"6. Output format: [\"{target_language} translation 1\", \"{target_language} translation 2\", ...]")
        prompt_parts.append("")
        prompt_parts.append("=" * 60)
        prompt_parts.append(f"SEGMENTS TO TRANSLATE ({len(texts)} total):")
        prompt_parts.append("=" * 60)
        prompt_parts.append("")
        
        # List each segment with clear ID and separator
        for i, (seg_id, text) in enumerate(zip(segment_ids, texts), 1):
            prompt_parts.append(f"[{seg_id}] SEGMENT {i}/{len(texts)}:")
            prompt_parts.append(f'"{text}"')
            prompt_parts.append("-" * 60)
        
        prompt_parts.append("")
        prompt_parts.append(f"Remember: Return EXACTLY {len(texts)} translations as a JSON array.")
        
        return "\n".join(prompt_parts)
    
    def _parse_and_validate_batch(
        self, 
        content: str, 
        expected_count: int,
        segment_ids: List[str]
    ) -> List[str]:
        """
        Parse batch response with STRICT validation
        """
        
        content = content.strip()
        
        # Remove code fences
        if content.startswith('```'):
            logger.info("Removing code fences from response...")
            lines = content.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            content = '\n'.join(lines).strip()
        
        try:
            translations = json.loads(content)
            
            if not isinstance(translations, list):
                logger.error(f"Response is not a JSON array, got type: {type(translations)}")
                raise ValueError("Response is not a JSON array")
            
            cleaned_translations = [str(t).strip() for t in translations]
            
            # CRITICAL VALIDATION
            if len(cleaned_translations) != expected_count:
                logger.error("")
                logger.error("VALIDATION FAILED:")
                logger.error(f"  Expected: {expected_count} translations")
                logger.error(f"  Received: {len(cleaned_translations)} translations")
                logger.error(f"  Missing/Extra: {abs(len(cleaned_translations) - expected_count)}")
                logger.error("")
                logger.error("Received translations:")
                for i, trans in enumerate(cleaned_translations, 1):
                    logger.error(f"  [{i}] {trans[:100]}...")
                logger.error("")
                
                # Don't auto-fix, let caller handle retry
                return cleaned_translations
            
            logger.info(f"✓ JSON parsed and validated: {len(cleaned_translations)} translations")
            return cleaned_translations
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse failed: {e}")
            logger.error("Raw content:")
            logger.error(content)
            
            # Fallback: try to extract array content
            logger.error("Attempting recovery...")
            
            # Try to find array boundaries
            start = content.find('[')
            end = content.rfind(']')
            
            if start >= 0 and end > start:
                array_content = content[start:end+1]
                try:
                    translations = json.loads(array_content)
                    if isinstance(translations, list):
                        cleaned = [str(t).strip() for t in translations]
                        logger.warning(f"Recovery succeeded: extracted {len(cleaned)} translations")
                        return cleaned
                except:
                    pass
            
            # Last resort: return empty array to trigger retry
            logger.error("Recovery failed - returning empty array to trigger retry")
            return []
    
    # ========== SINGLE SEGMENT TRANSLATION (unchanged but with better logging) ==========
    
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
        system_prompt = self._build_system_prompt_strict(tone)
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
                
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Translation failed after {max_retries} attempts: {e}")
                    return {
                        'translated_text': text,
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
        progress_callback: Optional[callable] = None,
        use_batch: bool = True,
        batch_size: int = 70  # Changed default from 80 to 50
    ) -> List[Dict]:
        """Main translation method"""
        
        if use_batch:
            return self.translate_segments_batch(
                segments, target_language, source_language,
                glossary, tone, batch_size, progress_callback
            )
        
        # Single segment mode
        results = []
        total = len(segments)
        
        logger.info(f"Single-segment mode: {total} segments")
        
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
        """Remove AI preambles from single translations"""
        cleanup_patterns = [
            "**CRITICAL RULES", "**Translated text:**",
            "Here is the translation:", "Translation:",
        ]
        
        for pattern in cleanup_patterns:
            if pattern.lower() in text.lower()[:200]:
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                for line in reversed(lines):
                    if not any(marker in line.lower() for marker in ["rule", "example", "translation:"]):
                        text = line
                        break
        
        return text.strip()
    
    def _wait_for_rate_limit(self):
        """Smart rate limiting"""
        now = time.time()
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        if len(self.request_times) >= self.max_rpm:
            sleep_time = 60 - (now - self.request_times[0]) + 0.1
            if sleep_time > 0:
                logger.info(f"⏸️  Rate limit pause: {sleep_time:.1f}s")
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
        
        return f"${cost:.4f}"