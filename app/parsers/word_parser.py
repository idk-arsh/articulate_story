"""
Word Document Parser for Articulate Storyline Translation
Handles .docx translation export format
"""

from docx import Document
from docx.shared import Pt, RGBColor
from typing import List, Dict, Tuple
from pathlib import Path


class WordSegment:
    """Represents a translatable segment from Word document"""
    
    def __init__(self, row_index: int, id_text: str, source_text: str, 
                 target_text: str = "", context: str = ""):
        self.row_index = row_index
        self.id_text = id_text  # ID or reference column
        self.source_text = source_text
        self.target_text = target_text
        self.context = context
        self.source_cell = None  # Reference to source cell
        self.target_cell = None  # Reference to target cell


class WordParser:
    """Parser for Word documents exported from Articulate Storyline"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.doc = None
        self.segments: List[WordSegment] = []
        self.source_col_index = None
        self.target_col_index = None
        self.id_col_index = None
        
    def parse(self) -> List[WordSegment]:
        """Parse Word document and extract segments"""
        try:
            self.doc = Document(self.file_path)
            
            # Find the main translation table
            table = self._find_translation_table()
            
            if not table:
                raise ValueError("No translation table found in document")
            
            # Identify column structure
            self._identify_columns(table)
            
            # Extract segments
            self.segments = self._extract_segments(table)
            
            return self.segments
            
        except Exception as e:
            raise RuntimeError(f"Failed to parse Word document: {str(e)}")
    
    def _find_translation_table(self):
        """Find the main translation table in the document"""
        # Look for tables with translation structure
        for table in self.doc.tables:
            if len(table.rows) > 1 and len(table.columns) >= 2:
                # Check if first row looks like headers
                first_row_text = ' '.join(cell.text.lower() for cell in table.rows[0].cells)
                
                # Common header patterns
                if any(keyword in first_row_text for keyword in 
                       ['original', 'translation', 'source', 'target', 'text']):
                    return table
        
        # If no clear header, return first table with multiple rows
        if self.doc.tables and len(self.doc.tables[0].rows) > 1:
            return self.doc.tables[0]
        
        return None
    
    def _identify_columns(self, table):
        """Identify which columns contain source, target, and ID"""
        if len(table.rows) == 0:
            raise ValueError("Table has no rows")
        
        header_row = table.rows[0]
        
        # Check header text to identify columns
        for i, cell in enumerate(header_row.cells):
            cell_text = cell.text.lower().strip()
            
            # Identify ID column
            if any(keyword in cell_text for keyword in ['id', '#', 'number', 'ref']):
                self.id_col_index = i
            
            # Identify source column
            elif any(keyword in cell_text for keyword in 
                     ['original', 'source', 'english', 'text']):
                self.source_col_index = i
            
            # Identify target/translation column
            elif any(keyword in cell_text for keyword in 
                     ['translation', 'target', 'translated']):
                self.target_col_index = i
        
        # If not found by headers, use default positions
        if self.source_col_index is None:
            # Assume source is first text column after ID (if exists)
            self.source_col_index = 1 if self.id_col_index == 0 else 0
        
        if self.target_col_index is None:
            # Assume target is last column or next to source
            self.target_col_index = len(header_row.cells) - 1
        
        print(f"Column mapping: ID={self.id_col_index}, Source={self.source_col_index}, Target={self.target_col_index}")
    
    def _extract_segments(self, table) -> List[WordSegment]:
        """Extract text segments from table"""
        segments = []
        
        # Skip header row (row 0)
        for row_idx, row in enumerate(table.rows[1:], start=1):
            try:
                cells = row.cells
                
                # Get ID if column exists
                id_text = ""
                if self.id_col_index is not None and self.id_col_index < len(cells):
                    id_text = cells[self.id_col_index].text.strip()
                
                # Get source text
                if self.source_col_index >= len(cells):
                    continue
                source_cell = cells[self.source_col_index]
                source_text = source_cell.text.strip()
                
                # Skip empty rows
                if not source_text:
                    continue
                
                # Get target text (may be empty)
                target_text = ""
                target_cell = None
                if self.target_col_index < len(cells):
                    target_cell = cells[self.target_col_index]
                    target_text = target_cell.text.strip()
                
                # Create segment
                segment = WordSegment(
                    row_index=row_idx,
                    id_text=id_text or f"row_{row_idx}",
                    source_text=source_text,
                    target_text=target_text,
                    context=f"Row {row_idx}"
                )
                
                # Store cell references for reconstruction
                segment.source_cell = source_cell
                segment.target_cell = target_cell
                
                segments.append(segment)
                
            except Exception as e:
                print(f"Warning: Failed to parse row {row_idx}: {e}")
                continue
        
        return segments
    
    def reconstruct(self, translated_segments: List[WordSegment], 
                   output_path: str) -> bool:
        """Reconstruct Word document with translations"""
        try:
            if not self.doc:
                raise ValueError("No document loaded. Call parse() first.")
            
            # Find the table again
            table = self._find_translation_table()
            
            if not table:
                raise ValueError("Translation table not found")
            
            # Update each segment's target cell
            for segment in translated_segments:
                if segment.row_index > len(table.rows) - 1:
                    print(f"Warning: Row {segment.row_index} out of range")
                    continue
                
                # Get the actual row (accounting for 0-indexing and header)
                row = table.rows[segment.row_index]
                
                if self.target_col_index >= len(row.cells):
                    print(f"Warning: Target column not found in row {segment.row_index}")
                    continue
                
                # Get target cell
                target_cell = row.cells[self.target_col_index]
                
                # Clear existing content
                target_cell.text = ""
                
                # Add translated text
                # Preserve basic formatting from source if possible
                if segment.target_text:
                    paragraph = target_cell.paragraphs[0] if target_cell.paragraphs else target_cell.add_paragraph()
                    paragraph.text = segment.target_text
                    
                    # Optional: Copy formatting from source cell
                    if segment.source_cell and segment.source_cell.paragraphs:
                        source_para = segment.source_cell.paragraphs[0]
                        if source_para.runs:
                            # Copy font properties from first run
                            source_run = source_para.runs[0]
                            if paragraph.runs:
                                target_run = paragraph.runs[0]
                                if source_run.bold:
                                    target_run.bold = source_run.bold
                                if source_run.italic:
                                    target_run.italic = source_run.italic
            
            # Save document
            self.doc.save(output_path)
            return True
            
        except Exception as e:
            print(f"Error reconstructing Word document: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def is_word_translation_format(file_path: str) -> bool:
        """Check if a Word file appears to be a Storyline translation export"""
        try:
            doc = Document(file_path)
            
            if not doc.tables:
                return False
            
            # Check first table for translation-like structure
            table = doc.tables[0]
            if len(table.rows) < 2 or len(table.columns) < 2:
                return False
            
            # Check header row for translation keywords
            header_text = ' '.join(cell.text.lower() for cell in table.rows[0].cells)
            
            return any(keyword in header_text for keyword in 
                      ['translation', 'original', 'source', 'target'])
            
        except:
            return False


def parse_word(file_path: str) -> List[WordSegment]:
    """Convenience function to parse a Word document"""
    parser = WordParser(file_path)
    return parser.parse()