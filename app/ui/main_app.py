"""
Articulate Storyline Translation Automation - Main UI
Powered by OpenRouter API
"""

import streamlit as st
import sys
from pathlib import Path
import os
import tempfile
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.parsers.xliff_parser import XLIFFParser
from app.translation.tag_manager import TagManager

# Check for API key
api_key_set = bool(os.getenv('OPENROUTER_API_KEY'))

# Page config
st.set_page_config(
    page_title="Storyline Translator",
    page_icon="🌐",
    layout="wide"
)

# Title and description
st.title("🌐 Articulate Storyline Translation Automation")
st.markdown("""
Automate translation of Articulate Storyline courses using AI via **OpenRouter**.
This tool translates XLIFF and Word export files while preserving formatting.
""")

# Quick start guide in expander
with st.expander("📖 Quick Start Guide"):
    st.markdown("""
    ### How to Use This Tool
    
    **Step 1: Export from Storyline**
    1. Open your Storyline course
    2. Go to **File → Translation → Export to XLIFF** (or Export for Translation)
    3. Save the file
    
    **Step 2: Translate**
    1. Upload the exported file here
    2. Select target language and tone
    3. (Optional) Add glossary terms
    4. Click "🚀 Start Translation"
    5. Download the translated file
    
    **Step 3: Import back to Storyline**
    1. In Storyline: **File → Translation → Import from XLIFF**
    2. Select the translated file
    3. Review slides and adjust layout if needed
    
    ### Supported Formats
    - ✅ XLIFF 1.2 and 2.0
    - ✅ Word (.docx) translation exports
    
    ### What Gets Translated
    - ✅ Slide text and shapes
    - ✅ Button labels
    - ✅ Feedback messages
    - ❌ Closed captions (manual)
    - ❌ Player UI text (manual)
    - ❌ Audio/video (manual)
    
    ### Tips
    - Use GPT-3.5 for testing (cheaper)
    - Use Claude 3.5 for production (best quality)
    - Always review translations before publishing
    - Test RTL languages (Arabic, Hebrew) carefully
    """)

st.divider()

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # API Status
    if api_key_set:
        st.success("✅ OpenRouter API key configured")
        
        # Show partial key for verification
        key = os.getenv('OPENROUTER_API_KEY', '')
        if key:
            st.caption(f"Key: {key[:15]}...")
        
        # Model selection
        model = st.selectbox(
            "AI Model",
            [
                "mistralai/devstral-2512:free",
                "qwen/qwen3-coder:free",
                "openai/gpt-oss-120b:free",
                "deepseek/deepseek-r1-0528:free", 
                "google/gemma-3-4b-it:free",
                "qwen/qwen3-235b-a22b:free"
            ],
            help="Choose the AI model for translation"
        )
    else:
        st.error("❌ OpenRouter API key not found")
        st.info("""
        **Setup Instructions:**
        1. Create a `.env` file in project root
        2. Add: `OPENROUTER_API_KEY=sk-or-v1-...`
        3. Restart Streamlit
        """)
        
        # Debug info
        with st.expander("🐛 Debug Info"):
            st.code(f"Current directory: {os.getcwd()}")
            st.code(f".env exists: {Path('.env').exists()}")
            if Path('.env').exists():
                st.code(f".env path: {Path('.env').absolute()}")
    
    st.divider()
    
    target_lang = st.selectbox(
        "Target Language",
        ["Spanish", "French", "German", "Arabic", "Hebrew", "Chinese", "Japanese"],
        help="Select the language to translate into"
    )
    
    tone = st.selectbox(
        "Translation Tone",
        ["Professional (default)", "Formal Polite", "Informal Friendly"],
        help="Choose the formality level for translations"
    )
    
    # Glossary input
    with st.expander("📚 Glossary (Optional)"):
        st.markdown("Add terms that should be translated consistently:")
        glossary_text = st.text_area(
            "Enter terms (one per line: source | target)",
            placeholder="Employee Handbook | Manual del Empleado\nProduct X | Product X",
            height=100,
            help="Format: 'source term | target term' or 'source term | DO NOT TRANSLATE'"
        )
        
        # Parse glossary
        glossary = {}
        if glossary_text:
            for line in glossary_text.strip().split('\n'):
                if '|' in line:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) == 2:
                        glossary[parts[0]] = parts[1]
        
        if glossary:
            st.success(f"✅ {len(glossary)} glossary terms loaded")
    
    st.divider()
    
    st.markdown("### 📊 Status")
    status_placeholder = st.empty()
    status_placeholder.info("Ready to translate")

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📁 File Upload")
    
    # Add sample file option
    use_sample = st.checkbox("🧪 Use sample file for testing", help="Try the tool with a built-in sample")
    
    if use_sample:
        sample_path = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "sample.xliff"
        if sample_path.exists():
            with open(sample_path, 'rb') as f:
                sample_data = f.read()
            
            # Create a proper fake uploaded file object
            class FakeUploadedFile:
                def __init__(self, name, data):
                    self.name = name
                    self._data = data
                
                def getvalue(self):
                    return self._data
                
                def read(self):
                    return self._data
            
            uploaded_file = FakeUploadedFile('sample.xliff', sample_data)
            st.info("📝 Using sample.xliff for demonstration")
        else:
            st.warning("Sample file not found")
            uploaded_file = None
    else:
        uploaded_file = st.file_uploader(
            "Upload Storyline Export File",
            type=["xliff", "xlf", "docx"],
            help="Upload an XLIFF or Word file exported from Articulate Storyline"
        )
    
    if uploaded_file:
        st.success(f"✅ File uploaded: {uploaded_file.name}")
        
        # Display file info
        file_size = len(uploaded_file.getvalue())
        st.info(f"📊 File size: {file_size:,} bytes ({file_size/1024:.1f} KB)")
        
        # Determine file type
        file_ext = Path(uploaded_file.name).suffix.lower()
        
        # Reset previous translation if new file uploaded
        if 'last_uploaded_file' not in st.session_state or st.session_state['last_uploaded_file'] != uploaded_file.name:
            # Clear previous translation
            for key in ['translated_file', 'translated_filename', 'qa_issues', 'qa_summary']:
                if key in st.session_state:
                    del st.session_state[key]
            st.session_state['last_uploaded_file'] = uploaded_file.name
        
        if file_ext in ['.xliff', '.xlf']:
            st.write("**File type:** XLIFF")
            
            # Try to parse the file
            with st.spinner("Parsing XLIFF file..."):
                try:
                    # Save temporarily using tempfile
                    with tempfile.NamedTemporaryFile(mode='wb', suffix='.xliff', delete=False) as tmp:
                        tmp.write(uploaded_file.getvalue())
                        temp_path = tmp.name
                    
                    # Parse
                    parser = XLIFFParser(temp_path)
                    segments = parser.parse()
                    
                    st.success(f"✅ Parsed successfully! Found {len(segments)} text segments.")
                    
                    # Show sample segments
                    with st.expander("📝 Preview Segments (first 5)"):
                        for i, seg in enumerate(segments[:5], 1):
                            st.markdown(f"**Segment {i}** (ID: {seg.id})")
                            st.code(seg.source_text[:200] + "..." if len(seg.source_text) > 200 else seg.source_text)
                            st.divider()
                    
                    # Store in session state for translation
                    st.session_state['parser'] = parser
                    st.session_state['segments'] = segments
                    st.session_state['temp_path'] = temp_path
                    
                    # Estimate translation cost
                    total_chars = sum(len(seg.source_text) for seg in segments)
                    est_tokens = total_chars * 1.3  # Rough estimate: 1 char ≈ 1.3 tokens
                    
                    with st.expander("💰 Cost Estimate"):
                        st.markdown(f"""
                        **Translation Estimates:**
                        - Segments: {len(segments)}
                        - Characters: {total_chars:,}
                        - Estimated tokens: ~{int(est_tokens):,}
                        
                        **Cost by Model:**
                        - GPT-3.5 Turbo: ~${(est_tokens/1000 * 0.0015):.3f}
                        - GPT-4 Turbo: ~${(est_tokens/1000 * 0.01):.3f}
                        - Claude 3.5 Sonnet: ~${(est_tokens/1000 * 0.003):.3f}
                        - Gemini Pro: ~${(est_tokens/1000 * 0.00025):.3f}
                        
                        *Estimates only - actual cost may vary*
                        """)
                    
                except Exception as e:
                    st.error(f"❌ Failed to parse file: {str(e)}")
                    st.exception(e)
        
        elif file_ext == '.docx':
            st.write("**File type:** Word Document")
            
            # Try to parse the Word file
            with st.spinner("Parsing Word document..."):
                try:
                    from app.parsers.word_parser import WordParser
                    
                    # Save temporarily
                    with tempfile.NamedTemporaryFile(mode='wb', suffix='.docx', delete=False) as tmp:
                        tmp.write(uploaded_file.getvalue())
                        temp_path = tmp.name
                    
                    # Check if it's a translation format
                    if not WordParser.is_word_translation_format(temp_path):
                        st.warning("⚠️ This doesn't appear to be a Storyline translation export. Attempting to parse anyway...")
                    
                    # Parse
                    parser = WordParser(temp_path)
                    segments = parser.parse()
                    
                    st.success(f"✅ Parsed successfully! Found {len(segments)} text segments.")
                    
                    # Show sample segments
                    with st.expander("📝 Preview Segments (first 5)"):
                        for i, seg in enumerate(segments[:5], 1):
                            st.markdown(f"**Segment {i}** (ID: {seg.id_text})")
                            st.code(seg.source_text[:200] + "..." if len(seg.source_text) > 200 else seg.source_text)
                            st.divider()
                    
                    # Store in session state for translation
                    st.session_state['parser'] = parser
                    st.session_state['segments'] = segments
                    st.session_state['temp_path'] = temp_path
                    st.session_state['file_type'] = 'word'
                    
                except Exception as e:
                    st.error(f"❌ Failed to parse file: {str(e)}")
                    st.exception(e)
        
        else:
            st.error("❌ Unsupported file type")

with col2:
    st.header("🔧 Actions")
    
    if uploaded_file and 'segments' in st.session_state:
        
        # Translation button
        if st.button("🚀 Start Translation", type="primary", use_container_width=True):
            
            if not api_key_set:
                st.error("⚠️ OpenRouter API key not configured! Please add it to your .env file.")
            else:
                # Import translator
                from app.translation.gpt_translator import GPTTranslator
                
                # Get settings
                tone_map = {
                    "Professional (default)": "Professional",
                    "Formal Polite": "Formal",
                    "Informal Friendly": "Informal"
                }
                selected_tone = tone_map.get(tone, "Professional")
                
                # Initialize translator
                with st.spinner("Initializing translator..."):
                    try:
                        translator = GPTTranslator(model=model if 'model' in locals() else None)
                        st.success(f"✅ Using model: {translator.model}")
                    except Exception as e:
                        st.error(f"Failed to initialize translator: {e}")
                        st.stop()
                
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Translate segments
                results = []
                failed_count = 0
                
                segments = st.session_state['segments']
                total = len(segments)
                
                for i, seg in enumerate(segments):
                    # Update progress
                    progress = (i + 1) / total
                    progress_bar.progress(progress)
                    status_text.text(f"Translating segment {i+1}/{total}: {seg.id}")
                    
                    # Translate
                    result = translator.translate_segment(
                        text=seg.source_text,
                        target_language=target_lang,
                        tone=selected_tone,
                        glossary=glossary if glossary else None
                    )
                    
                    if result['success']:
                        seg.target_text = result['translated_text']
                    else:
                        failed_count += 1
                        st.warning(f"⚠️ Segment {seg.id} failed: {result.get('error', 'Unknown error')}")
                    
                    results.append(result)
                
                # Translation complete
                status_text.empty()
                progress_bar.empty()
                
                if failed_count == 0:
                    st.success(f"✅ Translation complete! Translated {total} segments.")
                else:
                    st.warning(f"⚠️ Translation complete with {failed_count} failures out of {total} segments.")
                
                # Run QA checks
                with st.spinner("Running quality checks..."):
                    from app.qa.qa_rules import QAChecker
                    
                    qa_checker = QAChecker(glossary=glossary if glossary else None)
                    issues = qa_checker.check_all(segments, "English", target_lang)
                    summary = qa_checker.get_summary()
                    
                    st.session_state['qa_issues'] = issues
                    st.session_state['qa_summary'] = summary
                    
                    # Show QA summary
                    if summary['critical'] > 0:
                        st.error(f"🔴 {summary['critical']} Critical issues found!")
                    if summary['major'] > 0:
                        st.warning(f"🟠 {summary['major']} Major issues found")
                    if summary['minor'] > 0:
                        st.info(f"🔵 {summary['minor']} Minor issues found")
                    
                    if summary['total'] == 0:
                        st.success("✅ No issues found!")
                    else:
                        # Show issues in expandable section
                        with st.expander(f"🔍 View {summary['total']} QA Issues", expanded=summary['critical'] > 0):
                            # Group by severity
                            for severity in ['Critical', 'Major', 'Minor']:
                                severity_issues = [i for i in issues if i.severity == severity]
                                if severity_issues:
                                    icon = "🔴" if severity == "Critical" else "🟠" if severity == "Major" else "🔵"
                                    st.markdown(f"### {icon} {severity} ({len(severity_issues)})")
                                    
                                    for issue in severity_issues[:10]:  # Show first 10
                                        st.markdown(f"""
                                        **{issue.category}** - Segment: `{issue.segment_id}`  
                                        {issue.description}
                                        """)
                                        if issue.source_text or issue.target_text:
                                            col_a, col_b = st.columns(2)
                                            with col_a:
                                                st.caption("Source:")
                                                st.code(issue.source_text[:100], language=None)
                                            with col_b:
                                                st.caption("Target:")
                                                st.code(issue.target_text[:100], language=None)
                                        st.divider()
                                    
                                    if len(severity_issues) > 10:
                                        st.info(f"+ {len(severity_issues) - 10} more issues (download CSV for full list)")
                
                # Reconstruct file (XLIFF or Word)
                with st.spinner("Building translated file..."):
                    parser = st.session_state['parser']
                    file_type = st.session_state.get('file_type', 'xliff')
                    
                    # Create temp file for output
                    suffix = '.docx' if file_type == 'word' else '.xliff'
                    with tempfile.NamedTemporaryFile(mode='wb', suffix=suffix, delete=False) as tmp:
                        output_path = tmp.name
                    
                    success = parser.reconstruct(segments, output_path)
                    
                    if success:
                        # Read file for download
                        with open(output_path, 'rb') as f:
                            translated_bytes = f.read()
                        
                        # Cleanup temp file
                        try:
                            os.unlink(output_path)
                        except:
                            pass
                        
                        # Set download filename based on type
                        extension = 'docx' if file_type == 'word' else 'xliff'
                        st.session_state['translated_file'] = translated_bytes
                        st.session_state['translated_filename'] = f"translated_{target_lang}.{extension}"
                        
                        # Show stats
                        stats = translator.get_stats()
                        st.info(f"""
                        **Translation Statistics:**
                        - Segments: {total}
                        - Tokens used: {stats['total_tokens']:,}
                        - Estimated cost: {stats['estimated_cost']}
                        """)
                    else:
                        st.error("Failed to reconstruct XLIFF file")
        
        # Download button (if translation exists)
        if 'translated_file' in st.session_state:
            st.download_button(
                label="📥 Download Translated File",
                data=st.session_state['translated_file'],
                file_name=st.session_state['translated_filename'],
                mime="application/xml",
                use_container_width=True
            )
            
            # QA Report download
            if 'qa_issues' in st.session_state:
                import pandas as pd
                from app.qa.qa_rules import QAChecker
                
                qa_checker = QAChecker()
                qa_checker.issues = st.session_state['qa_issues']
                qa_data = qa_checker.to_dict_list()
                
                if qa_data:
                    df = pd.DataFrame(qa_data)
                    csv = df.to_csv(index=False)
                    
                    st.download_button(
                        label="📋 Download QA Report (CSV)",
                        data=csv,
                        file_name="qa_report.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
        
        st.divider()
        
        st.divider()
        
        # Test tag protection
        st.subheader("🧪 Test Tag Protection")
        
        if st.button("Test Tag Manager", use_container_width=True):
            with st.spinner("Testing tag protection..."):
                # Take first segment with tags
                test_segment = None
                for seg in st.session_state['segments']:
                    if '<' in seg.source_text or '%' in seg.source_text:
                        test_segment = seg
                        break
                
                if test_segment:
                    st.write("**Original text:**")
                    st.code(test_segment.source_text)
                    
                    # Protect tags
                    manager = TagManager()
                    protected, mapping = manager.protect_tags(test_segment.source_text)
                    
                    st.write("**Protected text (safe for GPT):**")
                    st.code(protected)
                    
                    st.write("**Tag mapping:**")
                    st.json(mapping)
                    
                    # Simulate restoration
                    restored = manager.restore_tags(protected, mapping)
                    st.write("**Restored text:**")
                    st.code(restored)
                    
                    if restored == test_segment.source_text:
                        st.success("✅ Tag protection/restoration works perfectly!")
                    else:
                        st.error("❌ Restoration mismatch!")
                else:
                    st.info("No segments with tags found in this file")
    
    else:
        st.info("👈 Upload a file to begin")

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; font-size: 0.8em;'>
    Storyline Translation Automation v0.1.0 (Sprint 1 - Parser MVP)<br>
    Built with Streamlit & Python
</div>
""", unsafe_allow_html=True)