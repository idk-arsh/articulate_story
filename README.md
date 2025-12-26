# Articulate Storyline Translation Automation

## AI powered translation tool for Articulate Storyline e-learning courses

Automate course localization for Articulate Storyline using OpenRouter models such as Claude, GPT 4, Gemini and others, while preserving formatting, variables, and course structure.

---

## Features

* AI based translation using multiple models through OpenRouter
* Support for XLIFF 1.2, XLIFF 2.0, and Word DOCX formats
* Full preservation of formatting tags, variables, and placeholders
* Automated quality checks for missing tags, incorrect numbers, and glossary violations
* Glossary enforcement to maintain consistent terminology
* Translation tone controls including Professional, Formal, and Informal
* Right to left language support for Arabic, Hebrew, and similar languages
* Pre translation cost estimation
* Real time progress tracking during translation
* Downloadable QA reports in CSV format

---

## Quick Start

### Prerequisites

* Python 3.10 or later
* pip package manager
* OpenRouter API key with access to supported models

  * Keys can be generated at [https://openrouter.ai/](https://openrouter.ai/)
  * Refer to OPENROUTER_SETUP.md for detailed configuration instructions

### Installation

1. Clone or download this repository

2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS or Linux
source venv/bin/activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Configure environment variables

```bash
cp .env.example .env

# Update the .env file with your OpenRouter API key
# OPENROUTER_API_KEY=sk-or-v1-...
# OPENAI_MODEL=openai/gpt-3.5-turbo or anthropic/claude-3.5-sonnet
```

5. Run the application

```bash
streamlit run app/ui/main_app.py
```

The application will be available at [http://localhost:8501](http://localhost:8501)

---

## How to Use

### 1. Export from Articulate Storyline

* Open the Storyline project
* Navigate to File, then Translation, then Export to XLIFF or Export for Translation
* Save the exported file locally

### 2. Translate

* Upload the exported file through the web interface
* Select the target language and desired tone
* Optionally add glossary terms to enforce consistent translations
* Start the translation process
* Review any QA findings
* Download the translated output

### 3. Import back into Storyline

* In Storyline, go to File, then Translation, then Import from XLIFF or Import
* Select the translated file
* Review slides and adjust layout or alignment if required
* Publish the localized course

---

## Testing

Run the following commands to validate individual components

```bash
# Validate XLIFF parsing
python tests/test_xliff_parser.py

# Validate Word document parsing
python tests/test_word_parser.py

# Verify OpenRouter connectivity
python test_openrouter_connection.py
```

---

## Tips and Best Practices

### Model Selection

* GPT 3.5 Turbo provides fast and inexpensive translations suitable for testing
* Claude 3.5 Sonnet offers the best overall translation quality and is recommended for production use
* GPT 4 Turbo delivers high quality output at a higher cost
* Gemini Pro is a cost effective option for large volume translations

### Glossary Configuration

Glossary entries follow the format

```
Source Term | Target Term
```

Example

```
Employee Handbook | Manual del Empleado
Product X | Product X
HR Department | Departamento de RRHH
```

To prevent translation of specific terms, use

```
CompanyName Inc | DO NOT TRANSLATE
```

### Right to Left Languages

* Text content translates correctly for RTL languages
* Manual alignment adjustments may be required after import
* Player UI orientation should be reviewed
* Full testing is recommended prior to publishing

### Post Import Validation

* Verify text does not overflow text containers
* Confirm variables remain functional
* Validate navigation and button behavior
* Check formatting such as bold and italics
* Confirm numerical values are accurate
* Ensure glossary terms are applied consistently

---

## Project Structure

```
storyline-translator/
├── app/
│   ├── parsers/          # XLIFF and Word parsers
│   ├── translation/      # Model integration and tag handling
│   ├── qa/               # Quality assurance checks
│   ├── ui/               # Streamlit interface
│   └── data/             # Glossaries and reference data
├── tests/                # Unit tests and fixtures
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
└── README.md             # Project documentation
```

---

## Troubleshooting

### API key not detected

* Confirm the .env file exists at the project root
* Verify the key begins with sk-or-v1-
* Restart Streamlit after updating environment variables

### File parsing errors

* Ensure the file was exported directly from Storyline
* Attempt both XLIFF and Word export options
* Verify the file is not corrupted

### Translation failures

* Confirm sufficient OpenRouter account credits
* Test with a smaller model such as GPT 3.5
* Verify network connectivity

### Import issues in Storyline

* Confirm the translated file includes state="translated"
* Re export the source file if needed
* Ensure the import format matches the export format

---

## Contributing

This tool is intended for internal use. Contributions are welcome

1. Create a feature branch
2. Add or update tests
3. Submit a pull request for review

---

## Documentation

* OPENROUTER_SETUP.md provides detailed API configuration guidance
* SOP document outlines the full development and execution plan

---

## Roadmap

### Completed

* XLIFF 1.2 and 2.0 parsing
* Word document parsing
* OpenRouter model integration
* Tag preservation system
* Automated QA checks
* Glossary support
* Streamlit based user interface

### Planned

* Translation memory support
* Batch processing for multiple files
* Save and resume translation progress
* Cost tracking at the project level
* User authentication
* Administrative dashboard

---

## Support

For issues or questions

* Review the troubleshooting section
* Consult OpenRouter documentation
* Contact the internal development team

---

## License

Internal use only. Not intended for public distribution

---

## Credits

Built using

* Streamlit for the web interface
* OpenRouter for model access
* lxml for XML processing
* python docx for Word document handling

---

Version 1.0.0
Last updated December 2024

## Quick Start

### Prerequisites

* Python 3.10 or later
* pip package manager
* OpenRouter API key with access to Claude, GPT, Gemini, and related models

  * Keys available at [https://openrouter.ai/](https://openrouter.ai/)
  * Refer to OPENROUTER_SETUP.md for setup instructions

### Installation

1. Clone or download this repository

2. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS or Linux
source venv/bin/activate
```

3. Install dependencies

```bash
pip install -r requirements.txt
```

4. Configure environment variables

```bash
cp .env.example .env

# Add your OpenRouter API key
# OPENROUTER_API_KEY=sk-or-v1-...
# OPENAI_MODEL=anthropic/claude-3.5-sonnet
```

### Running the Application

```bash
streamlit run app/ui/main_app.py
```

The application will be available at [http://localhost:8501](http://localhost:8501)

## Why OpenRouter

OpenRouter provides access to multiple large language models through a single API

* Anthropic Claude 3.5 Sonnet for high quality translations
* OpenAI GPT 4 for strong quality and performance balance
* Google Gemini for cost sensitive workloads
* Meta Llama for open source based models

Model selection can be changed directly in the UI without code changes

## Current Status

### Completed

* XLIFF 1.2 and 2.0 parsing
* Tag preservation system
* Initial Streamlit interface
* File upload and parsing
* Segment preview

### In Progress

* Model based translation integration
* Glossary management
* Word document parsing
* Automated QA checks
* Progress tracking

## Testing

To test with the sample file

1. Run the application
2. Upload tests/fixtures/sample.xliff
3. Use the tag manager test option

## Project Structure

```
storyline-translator/
├── app/
│   ├── parsers/          # XLIFF and Word parsers
│   ├── translation/      # Model integration and tag handling
│   ├── qa/               # Quality assurance checks
│   ├── ui/               # Streamlit interface
│   └── data/             # Glossaries and resources
├── tests/                # Test files and fixtures
├── requirements.txt      # Python dependencies
└── README.md             # Project documentation
```

## Development

### Adding Features

1. Create a feature branch
2. Implement changes and tests
3. Validate locally using sample XLIFF files
4. Submit a pull request for review

### Code Style

* Use type hints where appropriate
* Include docstrings for public functions and classes
* Keep functions small and focused
* Follow PEP 8 guidelines

## Known Issues

* Word document parsing is not fully implemented
* Model based translation requires manual API key testing
* UI polish is pending

## License

Internal use only. Not for public distribution

## Team

* Developer Parser and Backend
* Developer UI and Integration
* QA Tester
* Localization QA Tester

## Support

For questions or issues, contact the internal development team through established channels
