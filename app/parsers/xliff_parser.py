"""
XLIFF Parser for Articulate Storyline Translation
Handles both XLIFF 1.2 and 2.0 formats
"""

from lxml import etree
from typing import List, Dict, Optional
import re


class Segment:
    """Represents a translatable segment from XLIFF"""
    
    def __init__(self, id: str, source_text: str, target_text: str = "", 
                 element=None, context: str = ""):
        self.id = id
        self.source_text = source_text
        self.target_text = target_text
        self.element = element  # Reference to XML element for reconstruction
        self.context = context
        self.placeholder_map = {}  # Will store tag protection mapping


class XLIFFParser:
    """Parser for XLIFF files exported from Articulate Storyline"""
    
    # Namespaces for XLIFF versions
    NS_XLIFF_12 = {'xliff': 'urn:oasis:names:tc:xliff:document:1.2'}
    NS_XLIFF_20 = {'xliff': 'urn:oasis:names:tc:xliff:document:2.0'}
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.tree = None
        self.root = None
        self.version = None
        self.namespace = {}
        self.segments: List[Segment] = []
        
    def parse(self) -> List[Segment]:
        """Parse XLIFF file and extract segments"""
        try:
            # Parse XML
            self.tree = etree.parse(self.file_path)
            self.root = self.tree.getroot()
            
            # Detect version
            self._detect_version()
            
            # Extract segments based on version
            if self.version == "1.2":
                self.segments = self._parse_xliff_12()
            elif self.version == "2.0":
                self.segments = self._parse_xliff_20()
            else:
                raise ValueError(f"Unsupported XLIFF version: {self.version}")
            
            return self.segments
            
        except etree.XMLSyntaxError as e:
            raise ValueError(f"Invalid XML in XLIFF file: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Failed to parse XLIFF: {str(e)}")
    
    def _detect_version(self):
        """Detect XLIFF version from root element"""
        version_attr = self.root.get('version')
        
        if version_attr and version_attr.startswith('1.'):
            self.version = "1.2"
            self.namespace = self.NS_XLIFF_12
        elif version_attr and version_attr.startswith('2.'):
            self.version = "2.0"
            self.namespace = self.NS_XLIFF_20
        else:
            # Try to detect from namespace
            if 'xliff:document:1' in str(self.root.nsmap):
                self.version = "1.2"
                self.namespace = self.NS_XLIFF_12
            elif 'xliff:document:2' in str(self.root.nsmap):
                self.version = "2.0"
                self.namespace = self.NS_XLIFF_20
            else:
                # Default to 1.2 if unclear
                self.version = "1.2"
                self.namespace = {}
    
    def _parse_xliff_12(self) -> List[Segment]:
        """Parse XLIFF 1.2 format"""
        segments = []
        
        # Find all trans-unit elements - try multiple approaches
        # Method 1: With namespace
        trans_units = self.root.xpath('//xliff:trans-unit', namespaces=self.namespace)
        
        # Method 2: Without namespace prefix
        if not trans_units:
            trans_units = self.root.xpath('//trans-unit')
        
        # Method 3: Using local-name (namespace-agnostic)
        if not trans_units:
            trans_units = self.root.xpath('//*[local-name()="trans-unit"]')
        
        for unit in trans_units:
            try:
                unit_id = unit.get('id', '')
                
                # Get source element - try multiple approaches
                # Method 1: With namespace
                source_elem = unit.find('xliff:source', namespaces=self.namespace)
                
                # Method 2: Without namespace
                if source_elem is None:
                    source_elem = unit.find('source')
                
                # Method 3: Using local-name
                if source_elem is None:
                    source_elem = unit.xpath('.//*[local-name()="source"]')
                    if source_elem:
                        source_elem = source_elem[0]
                    else:
                        source_elem = None
                
                if source_elem is None:
                    print(f"Warning: No source element in trans-unit {unit_id}")
                    continue
                
                # Extract text with inline elements preserved
                source_text = self._extract_text_with_tags(source_elem)
                
                # Get target element (may be empty)
                # Try multiple methods
                target_elem = unit.find('xliff:target', namespaces=self.namespace)
                if target_elem is None:
                    target_elem = unit.find('target')
                if target_elem is None:
                    target_xpath = unit.xpath('.//*[local-name()="target"]')
                    if target_xpath:
                        target_elem = target_xpath[0]
                
                target_text = ""
                if target_elem is not None:
                    target_text = self._extract_text_with_tags(target_elem)
                
                # Get context if available (from notes or resname)
                context = unit.get('resname', '')
                
                segment = Segment(
                    id=unit_id,
                    source_text=source_text,
                    target_text=target_text,
                    element=unit,
                    context=context
                )
                
                segments.append(segment)
                
            except Exception as e:
                print(f"Warning: Failed to parse trans-unit {unit.get('id', 'unknown')}: {e}")
                continue
        
        return segments
    
    def _parse_xliff_20(self) -> List[Segment]:
        """Parse XLIFF 2.0 format"""
        segments = []
        
        # Find all unit elements
        units = self.root.xpath('//xliff:unit', namespaces=self.namespace)
        if not units:
            units = self.root.xpath('//unit')
        
        for unit in units:
            try:
                unit_id = unit.get('id', '')
                
                # In XLIFF 2.0, segments are nested in units
                segment_elems = unit.xpath('.//xliff:segment', namespaces=self.namespace)
                if not segment_elems:
                    segment_elems = unit.xpath('.//segment')
                
                for seg_elem in segment_elems:
                    source_elem = seg_elem.find('.//source', namespaces=self.namespace)
                    if source_elem is None:
                        source_elem = seg_elem.find('.//source')
                    
                    if source_elem is None:
                        continue
                    
                    source_text = self._extract_text_with_tags(source_elem)
                    
                    target_elem = seg_elem.find('.//target', namespaces=self.namespace)
                    if target_elem is None:
                        target_elem = seg_elem.find('.//target')
                    
                    target_text = ""
                    if target_elem is not None:
                        target_text = self._extract_text_with_tags(target_elem)
                    
                    segment = Segment(
                        id=f"{unit_id}_{seg_elem.get('id', '0')}",
                        source_text=source_text,
                        target_text=target_text,
                        element=seg_elem,
                        context=unit.get('name', '')
                    )
                    
                    segments.append(segment)
                    
            except Exception as e:
                print(f"Warning: Failed to parse unit {unit.get('id', 'unknown')}: {e}")
                continue
        
        return segments
    
    def _extract_text_with_tags(self, element) -> str:
        """
        Extract text from element, converting inline tags to placeholders.
        This preserves formatting tags like <x id="1"/> as markers.
        """
        if element is None:
            return ""
        
        # Get all text including from children
        text_parts = []
        
        # Add text before first child
        if element.text:
            text_parts.append(element.text)
        
        # Process children (inline elements like <x>)
        for child in element:
            # Represent inline tag as a placeholder
            # Remove namespace from the tag for cleaner output
            tag_str = etree.tostring(child, encoding='unicode').strip()
            
            # Clean up namespace declarations in inline tags
            # Replace xmlns="..." with nothing
            import re
            tag_str = re.sub(r'\s+xmlns="[^"]*"', '', tag_str)
            
            text_parts.append(tag_str)
            
            # Add tail text after the child
            if child.tail:
                text_parts.append(child.tail)
        
        return ''.join(text_parts)
    
    def reconstruct(self, translated_segments: List[Segment], 
                   output_path: str) -> bool:
        """
        Reconstruct XLIFF with translated text and save to file.
        
        Args:
            translated_segments: List of segments with target_text filled
            output_path: Path to save translated XLIFF
            
        Returns:
            True if successful
        """
        try:
            if not self.tree:
                raise ValueError("No parsed tree available. Call parse() first.")
            
            # Update segments in tree
            for segment in translated_segments:
                self._update_segment_in_tree(segment)
            
            # Set state attributes on all targets
            self._set_translation_state()
            
            # Write to file
            self.tree.write(
                output_path,
                encoding='utf-8',
                xml_declaration=True,
                pretty_print=True
            )
            
            return True
            
        except Exception as e:
            print(f"Error reconstructing XLIFF: {e}")
            return False
    
    def _update_segment_in_tree(self, segment: Segment):
            """Update a segment's target in the XML tree"""
            element = segment.element
            
            if element is None:
                print(f"Warning: segment {segment.id} has no element reference")
                return
            
            # Find source and target among ALL children (not just direct)
            source = None
            target = None
            
            # Look through direct children first
            for child in element:
                tag_local = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if tag_local == 'source':
                    source = child
                elif tag_local == 'target':
                    target = child
            
            # If target doesn't exist, create it
            if target is None:
                if source is not None:
                    # Insert target right after source
                    target = etree.Element('target')
                    source.addnext(target)
                else:
                    # No source found - this shouldn't happen, but handle it
                    # Try to find source with xpath as last resort
                    source_list = element.xpath('.//source')
                    if not source_list:
                        source_list = element.xpath('.//*[local-name()="source"]')
                    
                    if source_list:
                        source = source_list[0]
                        target = etree.Element('target')
                        source.addnext(target)
                    else:
                        # Still no source - just append target to element
                        print(f"Warning: No source found for segment {segment.id}, appending target")
                        target = etree.SubElement(element, 'target')
            
            # Now set the content
            if target is not None:
                # Clear existing content
                target.clear()
                
                # Set new translated text
                self._set_element_content_from_text(target, segment.target_text)
                
                # Set state attribute
                target.set('state', 'translated')
            else:
                print(f"Error: Could not create target for segment {segment.id}")

    def _set_element_content_from_text(self, element, text: str):
        """
        Set element content from text that may contain inline XML tags.
        This parses tag strings back into XML elements.
        """
        if not text:
            return
        
        # Try to parse text as XML fragment
        # Wrap in a temporary root to handle multiple tags
        try:
            wrapped = f"<root>{text}</root>"
            temp_root = etree.fromstring(wrapped)
            
            # Set text and append children
            element.text = temp_root.text
            for child in temp_root:
                element.append(child)
                
        except etree.XMLSyntaxError:
            # If parsing fails, just set as plain text
            element.text = text
    
    def _set_translation_state(self):
        """Set state='translated' on all target elements"""
        if self.version == "1.2":
            targets = self.root.xpath('//target', namespaces=self.namespace)
            if not targets:
                targets = self.root.xpath('//target')
            
            for target in targets:
                target.set('state', 'translated')
                
        elif self.version == "2.0":
            # In 2.0, state can be on segment or target
            segments = self.root.xpath('//xliff:segment', namespaces=self.namespace)
            if not segments:
                segments = self.root.xpath('//segment')
            
            for seg in segments:
                seg.set('state', 'translated')


# Utility function for quick parsing
def parse_xliff(file_path: str) -> List[Segment]:
    """Convenience function to parse an XLIFF file"""
    parser = XLIFFParser(file_path)
    return parser.parse()