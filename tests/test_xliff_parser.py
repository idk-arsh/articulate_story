"""
Unit tests for XLIFF Parser
"""

import pytest
from pathlib import Path
import sys

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.parsers.xliff_parser import XLIFFParser, Segment
from app.translation.tag_manager import TagManager


def test_parse_sample_xliff():
    """Test parsing the sample XLIFF file"""
    fixture_path = Path(__file__).parent / "fixtures" / "sample.xliff"
    
    parser = XLIFFParser(str(fixture_path))
    segments = parser.parse()
    
    # Debug: print what we found
    print(f"\nFound {len(segments)} segments:")
    for i, seg in enumerate(segments, 1):
        print(f"  {i}. ID: {seg.id}")
        print(f"     Text: {seg.source_text[:60]}...")
    
    # Should have 5 segments
    assert len(segments) == 5, f"Expected 5 segments, found {len(segments)}"
    
    # Check first segment
    first = segments[0]
    assert first.id == "slide1_text1"
    assert "Welcome" in first.source_text
    assert "%UserName%%" in first.source_text
    assert '<x id="1"' in first.source_text


def test_tag_protection():
    """Test tag protection and restoration"""
    manager = TagManager()
    
    test_text = "Click <x id='5'/> to continue %UserName%%."
    
    print(f"\nOriginal text: {test_text}")
    
    # Protect
    protected, mapping = manager.protect_tags(test_text)
    
    print(f"Protected text: {protected}")
    print(f"Mapping: {mapping}")
    
    # Should have 2 mappings (one for <x> tag, one for %UserName%%)
    assert len(mapping) >= 2, f"Expected at least 2 mappings, got {len(mapping)}"
    
    # Protected text should not contain original tags
    assert '<x' not in protected, "Protected text still contains <x tag"
    assert '%UserName%%' not in protected, "Protected text still contains %UserName%%"
    
    # Should contain tokens
    assert '[[TAG_' in protected, "Protected text doesn't contain tokens"
    
    # Restore
    restored = manager.restore_tags(protected, mapping)
    
    print(f"Restored text: {restored}")
    
    # Should match original
    assert restored == test_text, f"Restoration mismatch!\nExpected: {test_text}\nGot: {restored}"


def test_validation():
    """Test tag validation"""
    manager = TagManager()
    
    source = "Hello [[TAG_0_VARIABLE]] world [[TAG_1_XLIFF_TAG]]"
    target_good = "Hola [[TAG_0_VARIABLE]] mundo [[TAG_1_XLIFF_TAG]]"
    target_missing = "Hola mundo [[TAG_1_XLIFF_TAG]]"
    
    mapping = {
        "[[TAG_0_VARIABLE]]": "%Name%%",
        "[[TAG_1_XLIFF_TAG]]": "<x id='1'/>"
    }
    
    # Good translation
    issues_good = manager.validate_tags(source, target_good, mapping)
    assert len(issues_good['missing']) == 0
    assert len(issues_good['extra']) == 0
    
    # Missing tag
    issues_bad = manager.validate_tags(source, target_missing, mapping)
    assert len(issues_bad['missing']) == 1
    assert '[[TAG_0_VARIABLE]]' in issues_bad['missing']


def test_xliff_reconstruction():
    """Test reconstructing XLIFF with translations"""
    fixture_path = Path(__file__).parent / "fixtures" / "sample.xliff"
    output_path = Path(__file__).parent / "fixtures" / "output_test.xliff"
    
    # Parse
    parser = XLIFFParser(str(fixture_path))
    segments = parser.parse()
    
    # Add fake translations
    for seg in segments:
        seg.target_text = f"[TRANSLATED] {seg.source_text}"
    
    # Reconstruct
    success = parser.reconstruct(segments, str(output_path))
    assert success
    
    # Parse output to verify
    output_parser = XLIFFParser(str(output_path))
    output_segments = output_parser.parse()
    
    assert len(output_segments) == len(segments)
    assert "[TRANSLATED]" in output_segments[0].target_text
    
    # Cleanup
    output_path.unlink()


if __name__ == "__main__":
    # Run tests
    print("Running tests...")
    test_parse_sample_xliff()
    print("✅ test_parse_sample_xliff passed")
    
    test_tag_protection()
    print("✅ test_tag_protection passed")
    
    test_validation()
    print("✅ test_validation passed")
    
    test_xliff_reconstruction()
    print("✅ test_xliff_reconstruction passed")
    
    print("\n🎉 All tests passed!")