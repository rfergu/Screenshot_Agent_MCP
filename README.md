# Screenshot Organizer

AI-powered screenshot organization using local models (OCR + Vision) with GPT-4 orchestration.

## Features

- **🔍 Smart Analysis**: Uses Tesseract OCR for fast text extraction, falls back to Phi-3 Vision for images
- **📁 Automatic Organization**: Categorizes screenshots into code, errors, documentation, design, communication, memes, or other
- **💬 Natural Language Interface**: Chat with GPT-4 to organize your screenshots conversationally
- **⚡ Fast Processing**: OCR processes most screenshots in <50ms, vision model in <2s
- **🔒 Privacy-First**: Local AI processing (OCR + Vision), only GPT-4 orchestration uses OpenAI API
- **📊 Batch Processing**: Organize entire folders of screenshots at once
- **🗂️ Safe File Handling**: Conflict resolution, optional archiving, and safe filename generation

## Quick Start

### Prerequisites

- Python 3.11+
- Tesseract OCR installed
- OpenAI API key (for GPT-4 orchestration)

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd screenshot-organizer

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .

# Set up environment variables
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

### Install Tesseract OCR

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**Windows:**
Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

### Basic Usage

#### Interactive Chat Interface

```bash
# Start the interactive chat
python -m src.cli_interface --api-key YOUR_OPENAI_API_KEY

# Or set OPENAI_API_KEY environment variable
export OPENAI_API_KEY=your_key_here
python -m src.cli_interface
```

**Example conversation:**
```
You: Analyze this screenshot: /Users/me/Desktop/screenshot.png
Assistant: I'll analyze that screenshot for you...
[Analysis results]

You: Organize all screenshots in ~/Desktop/screenshots
Assistant: I found 15 screenshots. Should I organize them?
You: Yes
Assistant: Done! Organized 15 screenshots into categories...
```

#### MCP Server Mode

```bash
# Run as MCP server (for integration with other tools)
python -m src.screenshot_mcp_server
```

#### Python API

```python
from mcp_tools import MCPToolHandlers

# Initialize handlers
handlers = MCPToolHandlers()

# Analyze a screenshot
result = handlers.analyze_screenshot(
    path="/path/to/screenshot.png",
    force_vision=False  # Try OCR first
)

print(f"Category: {result['category']}")
print(f"Suggested filename: {result['suggested_filename']}")
print(f"Method used: {result['processing_method']}")

# Batch process a folder
stats = handlers.batch_process(
    folder="/path/to/screenshots",
    recursive=False,
    organize=True  # Automatically organize after analysis
)

print(f"Processed {stats['successful']} of {stats['total_files']} files")
print(f"Categories: {stats['categories_count']}")

# Organize a single file
result = handlers.organize_file(
    source_path="/path/to/screenshot.png",
    category="code",
    new_filename="python_function_example"
)
```

## Configuration

Configuration is managed via `config/default_config.yaml`:

```yaml
processing:
  ocr_min_words: 10  # Minimum words for OCR to be considered sufficient
  vision_timeout: 30
  batch_size: 50

organization:
  base_folder: "~/Screenshots/organized"
  categories:
    - code
    - errors
    - documentation
    - design
    - communication
    - memes
    - other
  keep_originals: true  # Keep copies in _originals folder

models:
  phi3_vision:
    max_tokens: 200
    temperature: 0.3

api:
  openai_model: "gpt-4-turbo-preview"
  max_context_length: 8000

logging:
  level: INFO
  file: screenshot_organizer.log
```

Override settings using environment variables:
```bash
export OPENAI_API_KEY=your_key
export MCP_SERVER_PORT=3000
export LOG_LEVEL=DEBUG
```

## Architecture

### Tiered Processing Approach

1. **OCR First**: Fast text extraction using Tesseract (~50ms)
2. **Keyword Classification**: Pattern matching on extracted text
3. **Vision Fallback**: Phi-3 Vision MLX for images without sufficient text (~1-2s)

This approach optimizes for speed while maintaining accuracy.

### Components

- **Processors**: OCR and Vision processors for image analysis
- **Classifiers**: Keyword-based classification engine
- **Organizers**: File management with safe operations
- **MCP Server**: Model Context Protocol server for tool integration
- **Chat Client**: GPT-4 orchestrated natural language interface

## Development

### Running Tests

```bash
# Run all tests
pytest -v

# Run specific test suite
pytest tests/test_ocr_processor.py -v

# Run integration tests
pytest tests/test_integration.py -v

# Run performance tests
pytest tests/test_performance.py -v -m performance
```

### Project Structure

```
screenshot-organizer/
├── src/
│   ├── processors/          # OCR and Vision processors
│   ├── classifiers/         # Keyword classification
│   ├── organizers/          # File organization logic
│   ├── utils/               # Config and logging utilities
│   ├── mcp_tools.py         # MCP tool handlers
│   ├── screenshot_mcp_server.py  # MCP server
│   ├── chat_client.py       # GPT-4 chat client
│   ├── cli_interface.py     # Interactive CLI
│   └── session_manager.py   # Session persistence
├── config/
│   └── default_config.yaml
├── tests/
│   ├── test_*.py           # Unit tests
│   ├── test_integration.py # Integration tests
│   └── test_performance.py # Performance tests
├── .env.example
├── requirements.txt
└── README.md
```

## CLI Commands

When using the interactive chat interface:

- `/help` - Show help message
- `/clear` - Clear conversation history
- `/stats` - Show organization statistics
- `/quit` or `/exit` - Exit the program

## Supported Categories

- **code**: Source code, programming screenshots
- **errors**: Error messages, stack traces, exceptions
- **documentation**: Guides, tutorials, API docs, README files
- **design**: UI mockups, wireframes, design systems, Figma
- **communication**: Slack, Discord, email, chat messages
- **memes**: Funny images, jokes
- **other**: Anything that doesn't fit above categories

## Performance Targets

- OCR processing: <50ms per screenshot
- Vision processing: <2s per screenshot
- Batch throughput: >10 files/second (with OCR)

## Troubleshooting

### Tesseract not found
```
Error: Tesseract not found
```
**Solution**: Install Tesseract OCR (see Installation section)

### Phi-3 Vision model not loading
```
Error: Failed to import phi-3-vision-mlx
```
**Solution**: This is macOS-specific. On other platforms, the vision model will use a placeholder. For full functionality on macOS:
```bash
pip install phi-3-vision-mlx==0.1.0
```

### OpenAI API errors
```
Error: OpenAI API key not provided
```
**Solution**: Set the OPENAI_API_KEY environment variable or use `--api-key` flag

### Permission denied when organizing files
**Solution**: Ensure the base organization folder is writable:
```bash
chmod 755 ~/Screenshots/organized
```

## License

[Add your license here]

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## Acknowledgments

- Tesseract OCR for fast text extraction
- Microsoft Phi-3 Vision for local image understanding
- OpenAI GPT-4 for intelligent orchestration
- MCP (Model Context Protocol) for tool integration
