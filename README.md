# Screenshot Organizer

AI-powered screenshot organization demonstrating production AI agent development with Microsoft Agent Framework.

## Features

- **🔍 Smart Analysis**: Uses Tesseract OCR for fast text extraction, GPT-4 Vision or local Phi-3 Vision for image analysis
- **📁 Automatic Organization**: Categorizes screenshots into code, errors, documentation, design, communication, memes, or other
- **💬 Natural Language Interface**: Chat with GPT-4 to organize your screenshots conversationally
- **⚡ Fast Processing**: OCR processes most screenshots in <50ms, vision model in <2s
- **🎯 Dual-Mode Operation**:
  - **Remote (Production)**: Full AI agent capabilities with reliable tool support
  - **Local (Testing)**: Quick testing of conversation flow without API costs
- **📊 Batch Processing**: Organize entire folders of screenshots at once
- **🗂️ Safe File Handling**: Conflict resolution, optional archiving, and safe filename generation

## Quick Start

### Prerequisites

**For Remote Mode (Production - Recommended):**
- Python 3.11+
- Azure OpenAI or AI Foundry credentials ([Get credentials](https://ai.azure.com))
- Tesseract OCR installed

**For Local Mode (Testing/Debugging Only):**
- Python 3.11+
- Azure AI Foundry CLI ([Installation guide](https://learn.microsoft.com/azure/ai-foundry/cli/))
- Phi-4-mini model (~2GB download)

### Installation

#### Step 1: Core Setup (Required)

```bash
# Clone the repository
git clone <repository-url>
cd screenshot-organizer

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

#### Step 2: Install Tesseract OCR

**macOS:**
```bash
brew install tesseract
```

**Ubuntu/Debian:**
```bash
sudo apt-get install tesseract-ocr
```

**Windows:**
Download from: https://github.com/UB-Mannheim/tesseract/wiki

#### Step 3: Choose Your Mode

**Option A: Remote Mode Setup (Recommended for Production)**

1. Get Azure credentials from https://ai.azure.com or Azure Portal

2. Set environment variables:
```bash
export AZURE_AI_CHAT_ENDPOINT=https://your-project.services.ai.azure.com/api/projects/your-project
export AZURE_AI_MODEL_DEPLOYMENT=gpt-4o
export AZURE_AI_CHAT_KEY=your_api_key
```

Supported endpoints:
- AI Foundry: `https://xxx.services.ai.azure.com/api/projects/xxx`
- Azure OpenAI: `https://xxx.cognitiveservices.azure.com`

3. Run:
```bash
python -m src.cli_interface  # Remote is default
```

**Option B: Local Mode Setup (Testing/Debugging Only)**

1. Install Azure AI Foundry CLI:

**macOS:**
```bash
brew install azure/ai-foundry/foundry
foundry --version  # Verify installation
```

**Linux/Windows:**
See: https://learn.microsoft.com/azure/ai-foundry/cli/

2. Download and setup Phi-4-mini:
```bash
# Download model (first time, ~2GB)
foundry model get phi-4-mini

# Start Foundry service
foundry service start

# Load the model
foundry model load phi-4-mini

# Verify it's running
foundry service status
# Should show: Service is running on http://127.0.0.1:<port>
```

3. Run (keep Foundry service running in separate terminal):
```bash
python -m src.cli_interface --local
```

**Note:** Local mode is for testing conversation flow only - no screenshot analysis or file organization capabilities.

### Basic Usage

#### Interactive Chat (Remote Mode)

```bash
python -m src.cli_interface  # Starts immediately in remote mode
```

**Example conversation:**
```
Assistant: Hi! I'm a Screenshot Organizer agent built with Microsoft Agent Framework.
           I can help you organize chaotic screenshot folders...
           Where do you typically save your screenshots?

You: /Users/me/Desktop/screenshots
Assistant: Perfect! Let me analyze the screenshots in that folder...
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

This project demonstrates **Microsoft Agent Framework WITH MCP Client Integration**.

### Unified Architecture

```
Agent Framework (Brain 🧠)
    ↓ contains
MCP Client Wrapper (EMBEDDED)
    ↓ calls via stdio
MCP Server (Hands 🤲)
    ↓ operates on
File System
```

**Key Principle:** The Agent Framework has an embedded MCP client that connects to an MCP server for all file operations.

### How It Works

1. **Agent Framework (Orchestrator)**:
   - Uses GPT-4 for intelligent decision-making
   - Understands user intent
   - Decides categorization and naming
   - Orchestrates tool calls

2. **MCP Client (Embedded Protocol Bridge)**:
   - Embedded inside Agent Framework
   - Manages MCP server subprocess
   - Provides tool wrappers
   - Handles stdio communication

3. **MCP Server (Tool Provider)**:
   - Runs as separate subprocess
   - Exposes low-level file operation tools
   - Returns facts (not decisions)
   - Mediates all file system access

4. **Processing Components**:
   - **OCR**: Fast text extraction using Tesseract (~50ms)
   - **Vision**: Phi-3 Vision MLX for image understanding (~2s)
   - **Keyword Classifier**: Fallback pattern matching

**All file system operations go through the MCP protocol** - demonstrating both Agent Framework capabilities and MCP standardization.

For detailed architecture documentation, see [ARCHITECTURE.md](ARCHITECTURE.md).

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
- Microsoft Phi-4-mini for local testing capabilities
- Azure OpenAI GPT-4 for production AI agent orchestration
- Microsoft Agent Framework for unified tool integration
