# Articulate Storyline Translation Automation

🌐 **AI-powered translation tool for Articulate Storyline e-learning courses**

Automate course localization using OpenRouter (Claude, GPT-4, Gemini, etc.) while preserving formatting, variables, and course structure.

---

## ✨ Features

- 🤖 **AI Translation** - Multiple models via OpenRouter (Claude 3.5, GPT-4, GPT-3.5, Gemini)
- 📄 **Dual Format Support** - XLIFF (1.2 & 2.0) and Word (.docx)
- 🛡️ **Tag Protection** - Preserves formatting tags, variables, and placeholders
- ✅ **Automated QA** - Detects missing tags, wrong numbers, glossary violations
- 📚 **Glossary Support** - Enforce consistent terminology
- 🎨 **Tone Control** - Professional, Formal, or Informal translations
- 🌍 **RTL Support** - Arabic, Hebrew, and other right-to-left languages
- 💰 **Cost Estimation** - See estimated costs before translating
- 📊 **Progress Tracking** - Real-time translation progress
- 📋 **QA Reports** - Downloadable CSV reports of translation issues

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- pip package manager
- **OpenRouter API key** (supports multiple AI models)
  - Get your key at: https://openrouter.ai/
  - See [OPENROUTER_SETUP.md](OPENROUTER_SETUP.md) for detailed setup

### Installation

1. **Clone or download this repository**

2. **Create a virtual environment:**
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your OpenRouter API key
# OPENROUTER_API_KEY=sk-or-v1-...
# OPENAI_MODEL=openai/gpt-3.5-turbo  # or anthropic/claude-3.5-sonnet
```

5. **Run the application:**
```bash
streamlit run app/ui/main_app.py
```

The app will open in your browser at `http://localhost:8501`

---

## 📖 How to Use

### 1. Export from Storyline
- Open your Storyline course
- Go to **File → Translation → Export to XLIFF** (or Export for Translation)
- Save the file

### 2. Translate
- Upload the exported file to the web app
- Select target language and tone
- (Optional) Add glossary terms for consistent translation
- Click "🚀 Start Translation"
- Review QA issues if any
- Download the translated file

### 3. Import back to Storyline
- In Storyline: **File → Translation → Import from XLIFF** (or Import)
- Select the translated file
- Review slides and adjust layout/alignment as needed
- Publish your translated course!

---

## 🧪 Testing

Run the test suites to verify everything works:

```bash
# Test XLIFF parser
python tests/test_xliff_parser.py

# Test Word parser
python tests/test_word_parser.py

# Test OpenRouter connection
python test_openrouter_connection.py
```

---

## 💡 Tips & Best Practices

### Choosing a Model
- **GPT-3.5 Turbo** - Fast, cheap, good for testing (~$0.03/course)
- **Claude 3.5 Sonnet** - Best quality, recommended for production (~$0.15/course)
- **GPT-4 Turbo** - High quality, more expensive (~$0.50/course)
- **Gemini Pro** - Very cheap, good for large volumes (~$0.01/course)

### Glossary Usage
Format: `source term | target term`
```
Employee Handbook | Manual del Empleado
Product X | Product X
HR Department | Departamento de RRHH
```

Use `DO NOT TRANSLATE` for terms that should stay in English:
```
CompanyName Inc | DO NOT TRANSLATE
```

### RTL Languages (Arabic, Hebrew)
- Text will translate correctly
- After import, manually adjust text alignment to right
- Check player UI orientation
- Test thoroughly before publishing

### What to Check After Import
- ✅ Text fits in text boxes (no overflow)
- ✅ Variables still work (`%Name%%` etc.)
- ✅ Buttons and navigation work
- ✅ Formatting preserved (bold, italic)
- ✅ Numbers are correct
- ✅ Glossary terms used consistently

---

## 📁 Project Structure

```
storyline-translator/
├── app/
│   ├── parsers/          # XLIFF and Word parsers
│   ├── translation/      # GPT integration and tag management
│   ├── qa/              # Quality assurance checks
│   ├── ui/              # Streamlit interface
│   └── data/            # Glossaries and resources
├── tests/               # Test files and fixtures
├── requirements.txt     # Python dependencies
├── .env.example        # Environment template
└── README.md           # This file
```

---

## 🐛 Troubleshooting

### "API key not found"
- Make sure `.env` file exists in project root
- Check that key starts with `sk-or-v1-`
- Restart Streamlit after editing .env

### "Failed to parse file"
- Ensure file is exported from Storyline (not manually created)
- Try both XLIFF and Word export options
- Check file isn't corrupted

### Translation fails
- Verify you have credits in OpenRouter account
- Try a smaller model (GPT-3.5) first
- Check internet connection

### Import to Storyline fails
- Verify `state="translated"` is set (our tool does this automatically)
- Try re-exporting from Storyline
- Ensure you're importing correct format (XLIFF vs Word)

---

## 🤝 Contributing

This is an internal tool, but improvements are welcome:
1. Create feature branch
2. Write tests
3. Submit pull request

---

## 📚 Documentation

- [OpenRouter Setup Guide](OPENROUTER_SETUP.md) - Detailed API setup
- [SOP Document](Articulate%20Storyline%20Translation%20Automation%20â%20SOP%20&%20Execution%20Plan.docx) - Full development plan

---

## 🎯 Roadmap

### ✅ Completed (Sprint 1-2)
- XLIFF parser (1.2 & 2.0)
- Word document parser
- OpenRouter integration
- Tag protection system
- Automated QA checks
- Glossary support
- Streamlit UI

### 🚧 Planned Features
- [ ] Translation memory (reuse past translations)
- [ ] Batch processing (multiple files)
- [ ] Progress save/resume
- [ ] Cost tracking per project
- [ ] User authentication
- [ ] Admin dashboard

---

## 📞 Support

For issues or questions:
- Check [Troubleshooting](#-troubleshooting) section
- Review [OpenRouter docs](https://openrouter.ai/docs)
- Contact development team

---

## 📄 License

Internal use only - not for public distribution

---

## 🙏 Credits

Built with:
- [Streamlit](https://streamlit.io/) - Web interface
- [OpenRouter](https://openrouter.ai/) - AI model access
- [lxml](https://lxml.de/) - XML parsing
- [python-docx](https://python-docx.readthedocs.io/) - Word processing

---

**Version:** 1.0.0  
**Last Updated:** December 2024

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- pip package manager
- **OpenRouter API key** (supports multiple AI models: Claude, GPT-4, Gemini, etc.)
  - Get your key at: https://openrouter.ai/
  - See [OPENROUTER_SETUP.md](OPENROUTER_SETUP.md) for detailed setup instructions

### Installation

1. **Clone or download this repository**

2. **Create a virtual environment:**
```bash
python -m venv venv

# On Windows:
venv\Scripts\activate

# On Mac/Linux:
source venv/bin/activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables:**
```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your OpenRouter API key
# OPENROUTER_API_KEY=sk-or-v1-...
# OPENAI_MODEL=anthropic/claude-3.5-sonnet
```

### Running the Application

```bash
streamlit run app/ui/main_app.py
```

This will open the application in your browser at `http://localhost:8501`

## 🤖 Why OpenRouter?

OpenRouter provides access to multiple AI models through a single API:
- **Anthropic Claude** (3.5 Sonnet) - Best for translation quality
- **OpenAI GPT-4** - Great balance of quality and speed
- **Google Gemini** - Cost-effective option
- **Meta Llama** - Open source models

You can switch between models in the UI without changing code!

## 📋 Current Status (Sprint 1 - Week 1-2)

### ✅ Completed Features
- [x] XLIFF parser (supports 1.2 and 2.0)
- [x] Tag protection system (preserves formatting)
- [x] Basic Streamlit UI
- [x] File upload and parsing
- [x] Segment preview

### 🚧 In Progress
- [ ] GPT translation integration (Sprint 2)
- [ ] Glossary management (Sprint 2)
- [ ] Word document parser (Sprint 2)
- [ ] Automated QA checks (Sprint 3)
- [ ] Progress tracking (Sprint 3)

## 🧪 Testing

To test the parser with the sample file:

1. Run the application
2. Upload `tests/fixtures/sample.xliff`
3. Click "Test Tag Manager" to see tag protection in action

## 📁 Project Structure

```
storyline-translator/
├── app/
│   ├── parsers/          # XLIFF and Word parsers
│   ├── translation/      # GPT integration and tag management
│   ├── qa/              # Quality assurance checks
│   ├── ui/              # Streamlit interface
│   └── data/            # Glossaries and resources
├── tests/               # Test files and fixtures
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## 🔧 Development

### Adding New Features

1. Create feature branch: `git checkout -b feature/name`
2. Write code and tests
3. Test locally with sample XLIFF files
4. Create pull request for review

### Code Style

- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and single-purpose
- Follow PEP 8 style guidelines

## 📚 Documentation

- See `SOP.md` for complete development plan and specifications
- Each module has inline documentation
- User guide coming in Sprint 5

## 🐛 Known Issues

- Word document parsing not yet implemented
- GPT translation requires manual testing with API key
- UI needs polish (planned for Sprint 4)

## 📝 License

Internal use only - not for public distribution

## 👥 Team

- Developer 1: Parser & Backend
- Developer 2: UI & Integration
- Tester 1: QA & Testing
- Tester 2: Localization QA

## 📞 Support

For issues or questions, contact the development team via internal channels.