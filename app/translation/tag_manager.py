"""
Tag Protection Manager
Protects formatting tags and placeholders during translation
"""

import re
from typing import Dict, Tuple


class TagManager:
    """Manages protection and restoration of tags/placeholders"""
    
    # Patterns to match various placeholder types
    # Order matters! Process specific patterns before generic ones
    PATTERNS = {
        'xliff_tag': r'<x[^>]*?/>|<x[^>]*?>.*?</x>',  # <x id="1"/> or <x>...</x>
        'xliff_other': r'<(?:g|bx|ex|bpt|ept|ph)[^>]*?/>|<(?:g|bpt|ept)[^>]*?>.*?</(?:g|bpt|ept)>',
        'html_tag': r'<(?:b|i|u|strong|em|span)[^>]*?>.*?</(?:b|i|u|strong|em|span)>|<(?:br|hr)[^>]*?/>',
        'variable': r'%[^%\s]+%%',  # %Variable%% (double percent at end)
        # Note: We don't match arbitrary curly braces to avoid matching our own tokens
    }
    
    def __init__(self):
        self.token_counter = 0
        
    def protect_tags(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Replace tags/placeholders with protection tokens.
        
        Args:
            text: Original text with tags
            
        Returns:
            Tuple of (protected_text, mapping_dict)
            where mapping_dict maps tokens back to original tags
        """
        mapping = {}
        protected_text = text
        
        # Process each pattern type
        for pattern_name, pattern in self.PATTERNS.items():
            protected_text, pattern_map = self._protect_pattern(
                protected_text, pattern, pattern_name
            )
            mapping.update(pattern_map)
        
        return protected_text, mapping
    
    def _protect_pattern(self, text: str, pattern: str, 
                        pattern_type: str) -> Tuple[str, Dict[str, str]]:
        """Protect a specific pattern in text"""
        mapping = {}
        
        def replace_with_token(match):
            original = match.group(0)
            token = self._generate_token(pattern_type)
            mapping[token] = original
            return token
        
        protected = re.sub(pattern, replace_with_token, text)
        return protected, mapping
    
    def _generate_token(self, pattern_type: str) -> str:
        """Generate a unique protection token"""
        # Use double brackets to make tokens more distinctive and avoid conflicts
        token = f"[[TAG_{self.token_counter}_{pattern_type.upper()}]]"
        self.token_counter += 1
        return token
    
    def restore_tags(self, text: str, mapping: Dict[str, str]) -> str:
        """
        Restore original tags from protection tokens.
        
        Args:
            text: Text with protection tokens
            mapping: Dictionary mapping tokens to original tags
            
        Returns:
            Text with original tags restored
        """
        restored = text
        
        # Replace tokens with original tags
        for token, original in mapping.items():
            restored = restored.replace(token, original)
        
        return restored
    
    def validate_tags(self, source_text: str, target_text: str, 
                     mapping: Dict[str, str]) -> Dict[str, list]:
        """
        Validate that all protected tags are present in target.
        
        Args:
            source_text: Original source text (protected)
            target_text: Translated text (should have same tokens)
            mapping: Token mapping
            
        Returns:
            Dictionary with validation issues:
            {
                'missing': [list of missing tokens],
                'extra': [list of extra tokens],
                'order_changed': bool
            }
        """
        issues = {
            'missing': [],
            'extra': [],
            'order_changed': False
        }
        
        # Find all tokens in source and target
        source_tokens = self._find_tokens(source_text, mapping)
        target_tokens = self._find_tokens(target_text, mapping)
        
        # Check for missing tokens
        missing = set(source_tokens) - set(target_tokens)
        issues['missing'] = list(missing)
        
        # Check for extra tokens (shouldn't happen, but validate)
        extra = set(target_tokens) - set(source_tokens)
        issues['extra'] = list(extra)
        
        # Check if order changed (might be okay linguistically, but flag it)
        if source_tokens != target_tokens and len(missing) == 0 and len(extra) == 0:
            issues['order_changed'] = True
        
        return issues
    
    def _find_tokens(self, text: str, mapping: Dict[str, str]) -> list:
        """Find all protection tokens in text in order"""
        tokens = []
        for token in mapping.keys():
            # Count occurrences
            count = text.count(token)
            tokens.extend([token] * count)
        
        # Sort by position in text
        def token_position(token):
            pos = text.find(token)
            return pos if pos != -1 else float('inf')
        
        tokens.sort(key=token_position)
        return tokens
    
    def get_prompt_instructions(self) -> str:
        """
        Get instructions to include in GPT prompt about tag protection.
        
        Returns:
            String with instructions for GPT
        """
        return """CRITICAL RULES FOR PLACEHOLDERS:
1. Do NOT translate or modify any text inside double square brackets like [[TAG_0_XLIFF_TAG]]
2. These are formatting codes and MUST appear in your translation exactly as shown
3. Keep placeholders in approximately the same position in the sentence
4. Examples:
   - Source: "Click [[TAG_0_XLIFF_TAG]] to continue"
   - Target: "Cliquez sur [[TAG_0_XLIFF_TAG]] pour continuer"
   
If you see [[TAG_...]], copy it EXACTLY into your translation."""


# Convenience functions
def protect_text(text: str) -> Tuple[str, Dict[str, str]]:
    """Quick function to protect a text string"""
    manager = TagManager()
    return manager.protect_tags(text)


def restore_text(text: str, mapping: Dict[str, str]) -> str:
    """Quick function to restore tags in text"""
    manager = TagManager()
    return manager.restore_tags(text, mapping)


def validate_translation(source: str, target: str, mapping: Dict[str, str]) -> Dict:
    """Quick validation function"""
    manager = TagManager()
    return manager.validate_tags(source, target, mapping)