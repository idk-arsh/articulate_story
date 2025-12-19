"""
Quality Assurance Rules for Translation
Checks for common translation errors
"""

from typing import List, Dict
import re


class QAIssue:
    """Represents a QA issue found in translation"""
    
    def __init__(self, segment_id: str, severity: str, category: str, 
                 description: str, source_text: str = "", target_text: str = ""):
        self.segment_id = segment_id
        self.severity = severity  # Critical, Major, Minor
        self.category = category  # e.g., "Placeholder", "Length", "Glossary"
        self.description = description
        self.source_text = source_text
        self.target_text = target_text


class QAChecker:
    """Performs quality assurance checks on translations"""
    
    def __init__(self, glossary: Dict[str, str] = None):
        self.glossary = glossary or {}
        self.issues: List[QAIssue] = []
    
    def check_all(self, segments: List, source_language: str = "English", 
                  target_language: str = "Spanish") -> List[QAIssue]:
        """Run all QA checks on segments"""
        self.issues = []
        
        for seg in segments:
            # Skip if no translation
            if not seg.target_text:
                self.issues.append(QAIssue(
                    segment_id=seg.id,
                    severity="Critical",
                    category="Missing Translation",
                    description="Segment has no translation",
                    source_text=seg.source_text,
                    target_text=""
                ))
                continue
            
            # Run individual checks
            self._check_placeholders(seg)
            self._check_length(seg)
            self._check_glossary(seg)
            self._check_numbers(seg)
            self._check_punctuation(seg)
            self._check_untranslated(seg, source_language, target_language)
        
        return self.issues
    
    def _check_placeholders(self, seg):
        """Check that all placeholders are preserved"""
        # Find all [[TAG_...]] tokens
        source_tags = re.findall(r'\[\[TAG_\d+_[A-Z_]+\]\]', seg.source_text)
        target_tags = re.findall(r'\[\[TAG_\d+_[A-Z_]+\]\]', seg.target_text)
        
        # Find XLIFF <x> tags
        source_x = re.findall(r'<x[^>]*?/?>', seg.source_text)
        target_x = re.findall(r'<x[^>]*?/?>', seg.target_text)
        
        # Find %variable%% patterns
        source_vars = re.findall(r'%[^%\s]+%%', seg.source_text)
        target_vars = re.findall(r'%[^%\s]+%%', seg.target_text)
        
        # Check counts match
        if len(source_tags) != len(target_tags):
            self.issues.append(QAIssue(
                segment_id=seg.id,
                severity="Critical",
                category="Placeholder",
                description=f"Tag count mismatch: {len(source_tags)} in source, {len(target_tags)} in target",
                source_text=seg.source_text[:100],
                target_text=seg.target_text[:100]
            ))
        
        if len(source_x) != len(target_x):
            self.issues.append(QAIssue(
                segment_id=seg.id,
                severity="Critical",
                category="Placeholder",
                description=f"XLIFF tag mismatch: {len(source_x)} in source, {len(target_x)} in target",
                source_text=seg.source_text[:100],
                target_text=seg.target_text[:100]
            ))
        
        if len(source_vars) != len(target_vars):
            self.issues.append(QAIssue(
                segment_id=seg.id,
                severity="Critical",
                category="Variable",
                description=f"Variable count mismatch: {len(source_vars)} in source, {len(target_vars)} in target",
                source_text=seg.source_text[:100],
                target_text=seg.target_text[:100]
            ))
        
        # Check for missing specific tags
        for tag in source_tags:
            if tag not in seg.target_text:
                self.issues.append(QAIssue(
                    segment_id=seg.id,
                    severity="Critical",
                    category="Placeholder",
                    description=f"Missing placeholder: {tag}",
                    source_text=seg.source_text[:100],
                    target_text=seg.target_text[:100]
                ))
    
    def _check_length(self, seg):
        """Check for significant length differences"""
        source_len = len(seg.source_text.strip())
        target_len = len(seg.target_text.strip())
        
        if source_len == 0:
            return
        
        ratio = target_len / source_len
        
        # Flag if target is less than 50% or more than 200% of source
        if ratio < 0.5:
            self.issues.append(QAIssue(
                segment_id=seg.id,
                severity="Major",
                category="Length",
                description=f"Target much shorter than source ({target_len} vs {source_len} chars, {ratio:.0%})",
                source_text=seg.source_text[:100],
                target_text=seg.target_text[:100]
            ))
        elif ratio > 2.0:
            self.issues.append(QAIssue(
                segment_id=seg.id,
                severity="Major",
                category="Length",
                description=f"Target much longer than source ({target_len} vs {source_len} chars, {ratio:.0%})",
                source_text=seg.source_text[:100],
                target_text=seg.target_text[:100]
            ))
        elif ratio > 1.5:
            self.issues.append(QAIssue(
                segment_id=seg.id,
                severity="Minor",
                category="Length",
                description=f"Target longer than source ({target_len} vs {source_len} chars, {ratio:.0%}), may overflow text box",
                source_text=seg.source_text[:100],
                target_text=seg.target_text[:100]
            ))
    
    def _check_glossary(self, seg):
        """Check glossary terms are used correctly"""
        if not self.glossary:
            return
        
        # Remove placeholders for checking
        source_clean = re.sub(r'\[\[TAG_\d+_[A-Z_]+\]\]', '', seg.source_text)
        target_clean = re.sub(r'\[\[TAG_\d+_[A-Z_]+\]\]', '', seg.target_text)
        
        for source_term, target_term in self.glossary.items():
            # Check if source term appears in source
            if source_term.lower() in source_clean.lower():
                # Check if correct translation appears in target
                if target_term.lower() == "do not translate":
                    # Term should remain in English
                    if source_term.lower() not in target_clean.lower():
                        self.issues.append(QAIssue(
                            segment_id=seg.id,
                            severity="Major",
                            category="Glossary",
                            description=f"Term '{source_term}' was translated but should remain unchanged",
                            source_text=seg.source_text[:100],
                            target_text=seg.target_text[:100]
                        ))
                else:
                    # Term should be translated to specific term
                    if target_term.lower() not in target_clean.lower():
                        self.issues.append(QAIssue(
                            segment_id=seg.id,
                            severity="Major",
                            category="Glossary",
                            description=f"Expected glossary term '{target_term}' for '{source_term}' not found",
                            source_text=seg.source_text[:100],
                            target_text=seg.target_text[:100]
                        ))
    
    def _check_numbers(self, seg):
        """Check that numbers are preserved"""
        # Extract numbers from source and target
        source_numbers = re.findall(r'\b\d+(?:\.\d+)?\b', seg.source_text)
        target_numbers = re.findall(r'\b\d+(?:\.\d+)?\b', seg.target_text)
        
        # Convert to sets for comparison
        source_set = set(source_numbers)
        target_set = set(target_numbers)
        
        # Check for missing numbers
        missing = source_set - target_set
        if missing:
            self.issues.append(QAIssue(
                segment_id=seg.id,
                severity="Critical",
                category="Number",
                description=f"Numbers missing in translation: {', '.join(missing)}",
                source_text=seg.source_text[:100],
                target_text=seg.target_text[:100]
            ))
        
        # Check for extra numbers
        extra = target_set - source_set
        if extra:
            self.issues.append(QAIssue(
                segment_id=seg.id,
                severity="Major",
                category="Number",
                description=f"Extra numbers in translation: {', '.join(extra)}",
                source_text=seg.source_text[:100],
                target_text=seg.target_text[:100]
            ))
    
    def _check_punctuation(self, seg):
        """Check punctuation consistency"""
        # Check ending punctuation
        source_end = seg.source_text.strip()[-1] if seg.source_text.strip() else ''
        target_end = seg.target_text.strip()[-1] if seg.target_text.strip() else ''
        
        if source_end in '.!?':
            if target_end not in '.!?。！？':  # Include CJK punctuation
                self.issues.append(QAIssue(
                    segment_id=seg.id,
                    severity="Minor",
                    category="Punctuation",
                    description=f"Source ends with '{source_end}' but target ends with '{target_end}'",
                    source_text=seg.source_text[:100],
                    target_text=seg.target_text[:100]
                ))
    
    def _check_untranslated(self, seg, source_lang: str, target_lang: str):
        """Check if text appears untranslated"""
        # Skip very short segments
        if len(seg.source_text.strip()) < 10:
            return
        
        # Remove placeholders for comparison
        source_clean = re.sub(r'<[^>]+>', '', seg.source_text)
        source_clean = re.sub(r'%[^%]+%%?', '', source_clean)
        source_clean = re.sub(r'\[\[TAG_\d+_[A-Z_]+\]\]', '', source_clean)
        source_clean = source_clean.strip()
        
        target_clean = re.sub(r'<[^>]+>', '', seg.target_text)
        target_clean = re.sub(r'%[^%]+%%?', '', target_clean)
        target_clean = re.sub(r'\[\[TAG_\d+_[A-Z_]+\]\]', '', target_clean)
        target_clean = target_clean.strip()
        
        # If source and target are identical (ignoring case), might be untranslated
        if source_clean.lower() == target_clean.lower() and len(source_clean) > 15:
            self.issues.append(QAIssue(
                segment_id=seg.id,
                severity="Major",
                category="Untranslated",
                description="Text appears to be untranslated (identical to source)",
                source_text=seg.source_text[:100],
                target_text=seg.target_text[:100]
            ))
    
    def get_summary(self) -> Dict:
        """Get summary of issues by severity"""
        critical = sum(1 for i in self.issues if i.severity == "Critical")
        major = sum(1 for i in self.issues if i.severity == "Major")
        minor = sum(1 for i in self.issues if i.severity == "Minor")
        
        return {
            "critical": critical,
            "major": major,
            "minor": minor,
            "total": len(self.issues)
        }
    
    def to_dict_list(self) -> List[Dict]:
        """Convert issues to list of dictionaries for export"""
        return [
            {
                "segment_id": issue.segment_id,
                "severity": issue.severity,
                "category": issue.category,
                "description": issue.description,
                "source": issue.source_text,
                "target": issue.target_text
            }
            for issue in self.issues
        ]