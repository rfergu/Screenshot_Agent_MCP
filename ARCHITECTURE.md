# Screenshot Organizer - System Architecture

**Version:** 1.0
**Last Updated:** 2025-11-12
**Project:** AI-Powered Screenshot Organization with MCP Integration

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Principles](#architecture-principles)
3. [System Components](#system-components)
4. [Architecture Diagram](#architecture-diagram)
5. [Dual-Mode Operation](#dual-mode-operation)
6. [MCP Integration](#mcp-integration)
7. [Data Flow](#data-flow)
8. [File Structure](#file-structure)
9. [Key Design Decisions](#key-design-decisions)
10. [Technology Stack](#technology-stack)

---

## Overview

The Screenshot Organizer is an AI-powered system that automatically analyzes, categorizes, and organizes screenshot files using:

**Microsoft Agent Framework WITH MCP Client Integration**

The architecture combines:
- **Microsoft Agent Framework** - AI agent orchestration (the brain)
- **MCP Client (embedded)** - Connects Agent Framework to MCP Server
- **MCP Server** - Provides file operation tools (the hands)
- **Azure OpenAI (GPT-4)** - Intelligent decision-making
- **Local AI Models** - OCR (Tesseract) and Vision (Phi-3) processing

**Key Point:** The Agent Framework contains an embedded MCP client that calls the MCP server for all file operations. This is not an "either/or" choice - it's a unified architecture.

---

## 🎯 Critical Architectural Principle

**The system is: Microsoft Agent Framework WITH MCP Client Integration**

```
NOT: Agent Framework OR MCP
YES: Agent Framework WITH MCP Client → MCP Server
```

This means:
1. The Agent Framework is the orchestrator (the brain)
2. An MCP Client is embedded inside the Agent Framework
3. The MCP Client connects to an MCP Server (subprocess)
4. The MCP Server provides file operation tools
5. ALL file system access goes through the MCP protocol

**There is no choice between "Agent Framework mode" vs "MCP mode" - they work together as one unified system.**

---

### Core Functionality

1. **Analyze** screenshots using OCR or vision models
2. **Categorize** screenshots intelligently using GPT-4
3. **Organize** files into category folders with descriptive names
4. **Batch process** entire directories of screenshots

---

## Architecture Principles

### 0. Unified Architecture: Agent Framework WITH MCP Client

**This is NOT a choice between Agent Framework OR MCP - it's both working together:**

```
Agent Framework (Brain 🧠)
    ↓ contains
MCP Client Wrapper
    ↓ calls via stdio
MCP Server (Hands 🤲)
    ↓ operates on
File System
```

**The Agent Framework has an embedded MCP client that connects to the MCP server.** This is a single unified architecture where:
- Agent Framework provides the intelligence and orchestration
- MCP Client (embedded) provides the protocol communication
- MCP Server provides the file operation tools
- All file access goes through MCP protocol

### 1. Separation of Concerns

**Brain (Agent Framework + GPT-4 + MCP Client):**
- Understands user intent
- Makes intelligent categorization decisions
- Generates descriptive filenames
- Orchestrates workflow
- **Contains MCP client to call MCP server**

**Hands (MCP Server):**
- Provides low-level file operations
- Executes commands as instructed
- Returns facts, not decisions
- Mediates file system access

### 2. Protocol-First Design

All file system operations go through the Model Context Protocol (MCP):
- Standardized tool interface
- Process separation and security
- Works with any MCP-compatible client
- Clear boundaries between components

### 3. Production vs Testing Modes

**Remote Mode (Production):**
- GPT-4 with full tool support
- Reliable function calling
- Complete screenshot organization capabilities

**Local Mode (Testing):**
- Phi-4-mini for conversation testing
- No tools (small models unreliable)
- Same agent code, different capabilities

---

## System Components

### 1. Agent Framework Layer

**File:** `src/agent_client.py`

The Agent Framework layer provides the AI orchestration using Microsoft's Agent Framework SDK.

```
AgentClient
├─ ChatAgent (Microsoft Agent Framework)
│  ├─ Chat Client (Azure OpenAI or Local Foundry)
│  ├─ Instructions (System Prompt)
│  └─ Tools (MCP Tool Wrappers)
└─ Thread Management (Conversation State)
```

**Responsibilities:**
- Initialize chat client (remote or local)
- Create and manage conversation threads
- Pass user messages to agent
- Handle tool orchestration
- Serialize/deserialize conversation state

### 2. MCP Client Wrapper

**File:** `src/mcp_client_wrapper.py`

Bridges the Agent Framework and MCP Server, providing synchronous tool functions.

```
MCPClientWrapper
├─ MCP Server Lifecycle
│  ├─ Start subprocess (python -m src server)
│  ├─ Create stdio session
│  └─ Stop cleanup
├─ Tool Wrappers (sync → async)
│  ├─ list_screenshots()
│  ├─ analyze_screenshot()
│  ├─ get_categories()
│  ├─ create_category_folder()
│  └─ move_screenshot()
└─ Session Management
```

**Responsibilities:**
- Start MCP server as subprocess
- Manage MCP client session via stdio transport
- Provide synchronous wrappers for Agent Framework
- Handle async/sync conversion
- Clean up resources on exit

### 3. MCP Server

**File:** `src/screenshot_mcp_server.py`

Standalone MCP server that exposes low-level file operation tools.

```
ScreenshotMCPServer
├─ Server (mcp.server.Server)
│  └─ Stdio Transport
├─ Tool Registry
│  ├─ list_screenshots
│  ├─ analyze_screenshot
│  ├─ get_categories
│  ├─ categorize_screenshot (keyword fallback)
│  ├─ create_category_folder
│  ├─ move_screenshot
│  └─ generate_filename (simple utility)
└─ Tool Handlers (mcp_tools functions)
```

**Responsibilities:**
- Expose tools via MCP protocol
- Handle tool call requests
- Execute file operations
- Return results as JSON

### 4. MCP Tools

**File:** `src/mcp_tools.py`

Low-level "dumb" tools that perform file operations and return facts.

**7 Core Tools:**

1. **list_screenshots(directory, recursive, max_files)**
   - Lists screenshot files in a directory
   - Returns: `{files: [{path, filename, size_bytes, modified_time}], total_count, truncated}`

2. **analyze_screenshot(file_path, force_vision)**
   - Extracts content using OCR or vision model
   - Returns: `{extracted_text, vision_description, processing_method, word_count, success}`
   - **Does NOT categorize** - Agent decides category

3. **get_categories()**
   - Returns available categories with descriptions and keywords
   - Returns: `{categories: [{name, description, keywords}], default_category}`

4. **categorize_screenshot(text, available_categories)**
   - Simple keyword-based fallback classifier
   - Returns: `{suggested_category, confidence, matched_keywords, method}`
   - **Note:** Agent (GPT-4) should make final decision

5. **create_category_folder(category, base_dir)**
   - Creates a folder for organizing screenshots
   - Returns: `{folder_path, created, success}`

6. **move_screenshot(source_path, dest_folder, new_filename, keep_original)**
   - Moves or copies a file
   - Returns: `{original_path, new_path, operation, success}`

7. **generate_filename(original_filename, category, text, description)**
   - Simple filename generation utility
   - Returns: `{suggested_filename, extension, timestamp}`
   - **Note:** Agent (GPT-4) can generate better names

### 5. Processing Modules

**OCR Processor** (`src/processors/ocr_processor.py`)
- Uses Tesseract OCR to extract text from screenshots
- Fast (~50ms) for text-heavy images
- Checks for sufficient text (>10 words)

**Vision Processor** (`src/processors/vision_processor.py`)
- Uses Azure GPT-4o Vision model for image understanding
- Slower (~2s) but handles images without text
- Provides descriptions and categorization

**Keyword Classifier** (`src/classifiers/keyword_classifier.py`)
- Simple pattern-based categorization
- Fallback when GPT-4 not available
- Fast but less intelligent

**File Organizer** (`src/organizers/file_organizer.py`)
- Handles file moving and renaming
- Creates category folder structure
- Optional archival of originals

**Batch Processor** (`src/organizers/batch_processor.py`)
- Scans directories for screenshot files
- Supports recursive processing
- Filters by image extensions

### 6. CLI Interface

**File:** `src/cli_interface.py`

Interactive command-line interface for user interaction.

```
CLIInterface
├─ Agent Client Integration
├─ Session Management
├─ Rich Console UI
├─ Command Handling (/help, /clear, /quit)
└─ Chat Loop (async)
```

**Responsibilities:**
- Display welcome and help messages
- Handle user input and commands
- Pass messages to agent
- Display responses with formatting
- Save/load conversation sessions

### 7. Configuration & Utilities

**Configuration** (`src/utils/config.py`)
- YAML-based configuration
- Environment variable overrides
- Mode detection (local/remote)

**Logging** (`src/utils/logger.py`)
- Structured logging
- Per-module loggers
- Debug mode support

**Session Management** (`src/session_manager.py`)
- Persists conversation threads
- JSON-based storage
- Resume previous sessions

---

## Architecture Diagram

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                            USER                                  │
│                      (CLI Interface)                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────────────┐
                    │  CLI Interface  │
                    │  (Rich Console) │
                    └─────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              AGENT FRAMEWORK WITH MCP CLIENT                     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ AgentClient                                               │  │
│  │ ├─ ChatAgent (Microsoft Agent Framework)                 │  │
│  │ │  ├─ Chat Client (Azure OpenAI: GPT-4)                  │  │
│  │ │  ├─ Instructions (System Prompt)                       │  │
│  │ │  └─ Tools (MCP Tool Wrappers)                          │  │
│  │ │                                                         │  │
│  │ └─ MCP Client Wrapper (EMBEDDED) ←────────────────────┐  │  │
│  │    ├─ Manages MCP Server subprocess                   │  │  │
│  │    ├─ Stdio session to MCP Server                     │  │  │
│  │    └─ Provides tool wrappers to ChatAgent             │  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  BRAIN 🧠: Makes intelligent decisions                          │
│  • Understands user intent                                      │
│  • Decides categories using GPT-4 intelligence                  │
│  • Creates descriptive filenames                                │
│  • Orchestrates MCP tool calls via embedded client              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                     (stdio transport)
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       MCP SERVER LAYER                           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ ScreenshotMCPServer (subprocess)                          │  │
│  │ ├─ Server (stdio transport)                              │  │
│  │ ├─ Tool Registry (7 tools)                               │  │
│  │ └─ Tool Handlers                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  HANDS 🤲: Executes file operations                             │
│  • Returns facts (text, paths, metadata)                        │
│  • No decision-making logic                                     │
│  • Just executes commands                                       │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER                              │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ OCR          │  │ Vision       │  │ Keyword      │         │
│  │ Processor    │  │ Processor    │  │ Classifier   │         │
│  │ (Tesseract)  │  │ (Azure GPT-4o Vision)  │  │ (Patterns)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐                            │
│  │ File         │  │ Batch        │                            │
│  │ Organizer    │  │ Processor    │                            │
│  └──────────────┘  └──────────────┘                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                       FILE SYSTEM                                │
│                                                                  │
│  All access mediated through MCP protocol ✓                     │
│                                                                  │
│  ~/Screenshots/organized/                                       │
│  ├─ code/                                                       │
│  ├─ errors/                                                     │
│  ├─ documentation/                                              │
│  ├─ design/                                                     │
│  ├─ communication/                                              │
│  ├─ memes/                                                      │
│  └─ other/                                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Dual-Mode Operation

The system supports two distinct operation modes with **the same architecture** - the difference is whether MCP tools are available or not.

**Both modes use the same architecture: Agent Framework WITH MCP Client**

The only difference is:
- **Remote Mode:** MCP Client active, tools available (GPT-4 can use them reliably)
- **Local Mode:** MCP Client inactive, no tools (small models unreliable with function calling)

### Remote Mode (Production)

**Purpose:** Full AI agent capabilities for production use

**Components:**
- **Chat Client:** Azure OpenAI (GPT-4 or GPT-4o)
- **MCP Client:** ACTIVE - embedded in Agent Framework
- **MCP Server:** Running as subprocess
- **Tools:** 5 MCP tools available via client wrapper
- **Capabilities:** Full screenshot analysis and organization

**Tool Access:**
```
Agent Framework + MCP Client (embedded) → MCP Server → Tools → File System
```

**Architecture:**
```
AgentClient
├─ ChatAgent (GPT-4)
├─ MCP Client Wrapper ← ACTIVE
│  └─ Connected to MCP Server
└─ Tools: list_screenshots, analyze_screenshot, etc. ← AVAILABLE
```

**Configuration:**
```bash
export AZURE_AI_CHAT_ENDPOINT="https://xxx.services.ai.azure.com/..."
export AZURE_AI_CHAT_KEY="..."
export AZURE_AI_MODEL_DEPLOYMENT="gpt-4o"

python -m src chat --mode remote
```

**Features:**
- ✅ Intelligent categorization (GPT-4 understanding)
- ✅ Creative filename generation
- ✅ Complex workflow orchestration
- ✅ Reliable tool calling
- ✅ File system access via MCP protocol

---

### Local Mode (Testing Only)

**Purpose:** Quick testing of conversation flow and agent instructions

**Components:**
- **Chat Client:** Azure AI Foundry Local Inference (Phi-4-mini)
- **MCP Client:** INACTIVE - not started (small models unreliable with tools)
- **MCP Server:** Not running
- **Tools:** NONE (disabled due to model limitations)
- **Capabilities:** Basic chat only

**Same Architecture, No Tools:**
```
Agent Framework + MCP Client (inactive) → No MCP Server → No Tools
```

**Architecture:**
```
AgentClient
├─ ChatAgent (Phi-4-mini)
├─ MCP Client Wrapper ← INACTIVE (not started)
│  └─ MCP Server not launched
└─ Tools: [] ← EMPTY (no tools available)
```

**Configuration:**
```bash
# Start local Foundry service
foundry service start

python -m src chat --mode local
```

**Features:**
- ✅ Fast local inference (no API costs)
- ✅ Test conversation flow
- ✅ Verify agent instructions
- ❌ No screenshot analysis
- ❌ No file organization
- ❌ No tool support

**Why No Tools?**
Small models (Phi-4-mini, Phi-3.5-mini) have unreliable function calling:
- Malformed JSON in tool calls
- Incorrect parameter values
- Hallucinated tool names
- Not suitable for production file operations

---

## MCP Integration

### Why MCP?

The Model Context Protocol provides:

1. **Standardization:** Common protocol for tool access across LLMs
2. **Separation:** Tools run in separate process from agent
3. **Security:** File access mediated through controlled server
4. **Reusability:** Same tools work with any MCP client

### MCP Architecture

```
┌────────────────────────────────────────────────┐
│  Agent Framework WITH MCP Client (In-Process)  │
│  ┌──────────────────────────────────────────┐ │
│  │ ChatAgent (GPT-4)                        │ │
│  │ └─ Makes intelligent decisions          │ │
│  └──────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────┐ │
│  │ MCP Client Wrapper (EMBEDDED)            │ │
│  │ ├─ Manages MCP server subprocess        │ │
│  │ ├─ Provides tool wrappers               │ │
│  │ └─ Calls MCP server via stdio           │ │
│  └──────────────────────────────────────────┘ │
└────────────────────────────────────────────────┘
                   ↓
            (stdio transport)
                   ↓
┌────────────────────────────────────────────────┐
│  MCP Server (Subprocess)                       │
│  ├─ Exposes 7 low-level tools                 │
│  ├─ Handles tool call requests                │
│  └─ Returns JSON results                      │
└────────────────────────────────────────────────┘
                   ↓
┌────────────────────────────────────────────────┐
│  File System                                   │
│  (All access mediated through MCP) ✓           │
└────────────────────────────────────────────────┘
```

### MCP Client Wrapper (Embedded in Agent Framework)

The wrapper is **embedded inside the Agent Framework** and manages the MCP server lifecycle:

```python
# Create wrapper
wrapper = MCPClientWrapper()

# Start MCP server subprocess
await wrapper.start()

# Call tools synchronously (Agent Framework compatible)
files = wrapper.list_screenshots("/path/to/screenshots")
analysis = wrapper.analyze_screenshot("/path/to/file.png")
wrapper.create_category_folder("code")
wrapper.move_screenshot(source, dest, new_filename)

# Cleanup
await wrapper.stop()
```

### MCP Server Startup

When the wrapper starts, it:

1. **Spawns subprocess:** `python -m src server`
2. **Creates stdio streams:** Connect to subprocess stdin/stdout
3. **Initializes session:** MCP handshake and tool discovery
4. **Registers tools:** Makes tools available to Agent Framework

### Tool Call Flow

```
User: "Organize screenshots in ~/Desktop"
  ↓
GPT-4: "I need to list files first"
  ↓
Agent Framework: calls list_screenshots()
  ↓
MCP Wrapper: wrapper.list_screenshots("/Users/foo/Desktop")
  ↓
MCP Client: session.call_tool("list_screenshots", {"directory": "..."})
  ↓ (stdio)
MCP Server: Receives tool call request
  ↓
MCP Tools: list_screenshots() function executes
  ↓
File System: Directory scan
  ↓
MCP Server: Returns JSON result
  ↓ (stdio)
MCP Client: Parses response
  ↓
MCP Wrapper: Returns dict to Agent
  ↓
Agent Framework: Receives file list
  ↓
GPT-4: "I found 10 files. Now I'll analyze each one..."
```

---

## Data Flow

### Complete Screenshot Organization Flow

```
[1] User Request
    User: "Organize screenshots in ~/Desktop/screenshots"

    ↓

[2] Agent Understanding (GPT-4)
    • Parse intent: User wants to organize files
    • Plan workflow: List → Analyze → Categorize → Move
    • Start execution

    ↓

[3] List Files (MCP Tool)
    Tool: list_screenshots(directory="~/Desktop/screenshots")
    Returns: {
      files: [
        {path: "/Users/.../screenshot1.png", ...},
        {path: "/Users/.../screenshot2.png", ...}
      ],
      total_count: 2
    }

    ↓

[4] For Each File - Analyze (MCP Tool)
    Tool: analyze_screenshot(file_path="screenshot1.png")
    Returns: {
      extracted_text: "def login():\n    username = ...",
      processing_method: "ocr",
      word_count: 15,
      success: true
    }

    ↓

[5] Intelligent Categorization (GPT-4)
    GPT-4 reads extracted text
    GPT-4 understands: "This is Python code for authentication"
    GPT-4 decides: category = "code"
    (NOT keyword matching - actual understanding!)

    ↓

[6] Create Descriptive Filename (GPT-4)
    GPT-4 creates: "login_authentication_function_2025-11-12"
    (NOT simple utility - creative naming!)

    ↓

[7] Create Category Folder (MCP Tool)
    Tool: create_category_folder(category="code")
    Returns: {
      folder_path: "/Users/.../organized/code",
      created: true,
      success: true
    }

    ↓

[8] Move File (MCP Tool)
    Tool: move_screenshot(
      source_path="screenshot1.png",
      dest_folder="/Users/.../organized/code",
      new_filename="login_authentication_function_2025-11-12",
      keep_original=true
    )
    Returns: {
      original_path: "...",
      new_path: ".../code/login_authentication_function_2025-11-12.png",
      operation: "copy",
      success: true
    }

    ↓

[9] Repeat for All Files
    (Steps 4-8 for each screenshot)

    ↓

[10] Report to User (GPT-4)
     "I've organized 2 screenshots:
      • 1 code screenshot: login_authentication_function_2025-11-12.png
      • 1 error screenshot: database_connection_error_2025-11-12.png

      All files have been copied to organized folders while keeping originals."
```

### Key Insights

**Agent Provides Intelligence:**
- Understands content (not just keywords)
- Makes contextual decisions
- Creates meaningful names
- Orchestrates complex workflows

**MCP Provides Operations:**
- Lists files (just paths and metadata)
- Extracts text (just raw text)
- Creates folders (just mkdir)
- Moves files (just file operations)

**Separation is Clear:**
- Brain (Agent) decides WHAT to do
- Hands (MCP) execute HOW to do it

---

## File Structure

```
screenshot-organizer/
├── src/
│   ├── __init__.py
│   ├── __main__.py                    # CLI entry point
│   │
│   ├── agent_client.py                # Agent Framework client
│   ├── cli_interface.py               # Interactive CLI
│   ├── session_manager.py             # Conversation persistence
│   │
│   ├── mcp_client_wrapper.py          # MCP ↔ Agent Framework bridge
│   ├── screenshot_mcp_server.py       # MCP server
│   ├── mcp_tools.py                   # MCP tool implementations
│   │
│   ├── local_foundry_chat_client.py            # Local Foundry chat client
│   │
│   ├── processors/
│   │   ├── __init__.py
│   │   ├── ocr_processor.py           # Tesseract OCR
│   │   └── vision_processor.py        # Azure GPT-4o Vision
│   │
│   ├── classifiers/
│   │   ├── __init__.py
│   │   └── keyword_classifier.py      # Pattern-based classification
│   │
│   ├── organizers/
│   │   ├── __init__.py
│   │   ├── file_organizer.py          # File moving/renaming
│   │   └── batch_processor.py         # Directory scanning
│   │
│   └── utils/
│       ├── __init__.py
│       ├── config.py                  # YAML configuration
│       ├── logger.py                  # Structured logging
│       └── model_manager.py           # Dependency checking
│
├── scripts/
│   ├── test_mcp_client.py            # MCP protocol test
│   ├── test_mcp_wrapper.py           # Wrapper test
│   └── test_integration.py           # Full integration test
│
├── tests/
│   ├── test_*.py                     # Unit tests
│   └── ...
│
├── config/
│   └── config.yaml                   # Configuration file
│
├── .specify/
│   └── memory/
│       └── constitution.md           # Project governance
│
├── specs/
│   └── 001-screenshot-organizer/
│       └── spec.md                   # Formal specification
│
├── ARCHITECTURE.md                   # This file
├── README.md                         # User documentation
├── DEMO.md                           # Demo instructions
├── MCP_INTEGRATION_COMPLETE.md       # Integration summary
├── MCP_TOOL_DESIGN.md                # Tool design doc
│
└── requirements.txt                  # Python dependencies
```

---

## Key Design Decisions

### 1. Agent Framework WITH MCP Client Architecture

**Decision:** Use Microsoft Agent Framework with embedded MCP Client

**This is the core architectural decision - not "Agent Framework OR MCP" but "Agent Framework WITH MCP Client".**

**Why Agent Framework:**
- Built-in tool orchestration
- Automatic function calling with GPT-4
- Thread and conversation management
- Azure integration
- Production-ready error handling

**Why Embedded MCP Client:**
- Demonstrates MCP protocol capabilities
- Clear separation between agent (brain) and file operations (hands)
- Standardized tool interface
- Security via process isolation
- Works with any MCP server

**Architecture:**
```
Agent Framework (orchestrator)
    ↓ contains
MCP Client (protocol bridge)
    ↓ calls
MCP Server (tool provider)
    ↓ operates on
File System
```

**Benefits:**
- ✅ Single unified architecture
- ✅ Agent Framework provides intelligence
- ✅ MCP provides standardized tool access
- ✅ All file operations through MCP protocol
- ✅ Demonstrates best practices for both technologies

**Trade-offs:**
- Additional complexity (subprocess management)
- Slight latency overhead (stdio IPC)
- More moving parts to manage

---

### 2. Low-Level "Dumb" Tools

**Decision:** Tools return facts, not decisions

**Example:**
```python
# ❌ Bad: Tool makes decisions
analyze_screenshot() returns {
    "category": "code",  # Tool decided!
    "suggested_filename": "foo.png"  # Tool decided!
}

# ✅ Good: Tool returns facts
analyze_screenshot() returns {
    "extracted_text": "def login()...",  # Just facts
    "vision_description": "..."  # Just facts
}
# Agent (GPT-4) decides category and filename
```

**Rationale:**
- Maximizes GPT-4's intelligence
- Clear separation of concerns
- Tools are reusable in different contexts
- Agent has full control over logic

---

### 3. Dual-Mode Architecture (Remote vs Local)

**Decision:** Same agent code, different tool availability

**Rationale:**
- Local mode: Test conversation flow quickly (no API costs)
- Remote mode: Production with reliable tools
- Small models can't do function calling reliably
- Same codebase reduces maintenance

**Implementation:**
```python
if mode == "local":
    tools = []  # No tools
else:
    tools = mcp_tools  # MCP tools via wrapper
```

---

### 4. OCR → Vision Tiered Approach

**Decision:** Try OCR first, fall back to vision if needed

**Rationale:**
- OCR is fast (~50ms) for text-heavy screenshots
- Vision is slow (~2s) but handles non-text images
- Most screenshots have some text
- Efficient use of resources

**Flow:**
```python
if force_vision:
    use_vision()
else:
    ocr_result = try_ocr()
    if ocr_result.sufficient_text:
        use_ocr_result()
    else:
        use_vision()  # Fallback
```

---

### 5. Keep Originals by Default

**Decision:** Copy files instead of moving (configurable)

**Rationale:**
- Safety: Don't lose original files
- User can manually delete later
- Archive feature for auditing
- Configurable in config.yaml

---

### 6. Category System

**Decision:** Fixed set of 7 categories

**Categories:**
- `code` - Programming content
- `errors` - Error messages, stack traces
- `documentation` - Docs, specs, references
- `design` - UI mockups, graphics
- `communication` - Messages, emails, chats
- `memes` - Humorous images
- `other` - Catch-all

**Rationale:**
- Covers most common screenshot types
- Small enough to be manageable
- Large enough to be useful
- Extensible via configuration

---

## Technology Stack

### AI & ML

- **Azure OpenAI (GPT-4/GPT-4o)** - Agent intelligence, categorization, naming
- **Microsoft Agent Framework** - AI agent orchestration
- **Azure GPT-4o Vision** - Cloud vision model for image understanding
- **Tesseract OCR** - Fast text extraction from screenshots

### Protocol & Communication

- **Model Context Protocol (MCP)** - Standardized tool interface
- **Stdio Transport** - IPC between agent and MCP server
- **JSON-RPC** - Tool call format

### Python Libraries

- **agent-framework** - Microsoft's AI agent SDK
- **mcp** - Model Context Protocol SDK
- **azure-ai-inference** - Azure AI services
- **pytesseract** - Tesseract OCR wrapper
- **Pillow (PIL)** - Image processing
- **click** - CLI framework
- **rich** - Terminal UI
- **pydantic** - Data validation
- **pyyaml** - Configuration

### Development Tools

- **pytest** - Testing framework
- **black** - Code formatting
- **mypy** - Type checking (optional)

### Azure Services

- **Azure OpenAI** - GPT-4 endpoint
- **Azure AI Foundry** - Local inference (optional)

---

## Deployment Scenarios

### Scenario 1: Developer Workstation

```bash
# Local testing with Phi-4-mini
foundry service start
python -m src chat --mode local

# Production with GPT-4
export AZURE_AI_CHAT_ENDPOINT="..."
python -m src chat --mode remote
```

### Scenario 2: Claude Desktop Integration

```json
// ~/Library/Application Support/Claude/claude_desktop_config.json
{
  "mcpServers": {
    "screenshot-organizer": {
      "command": "python",
      "args": ["-m", "src", "server"],
      "cwd": "/path/to/screenshot-organizer"
    }
  }
}
```

Claude Desktop can now use screenshot organization tools directly!

### Scenario 3: Automation Script

```python
import asyncio
from src.agent_client import AgentClient

async def organize_weekly_screenshots():
    agent = AgentClient(mode="remote")
    await agent.async_init()

    thread = agent.get_new_thread()
    response = await agent.chat(
        "Organize all screenshots in ~/Desktop/Weekly from the past week",
        thread=thread
    )

    await agent.cleanup()
    return response

asyncio.run(organize_weekly_screenshots())
```

---

## Performance Characteristics

### Latency

- **OCR Processing:** ~50ms per screenshot
- **Vision Processing:** ~2s per screenshot
- **GPT-4 API Call:** ~1-3s per request
- **MCP Tool Call:** ~5-10ms overhead
- **File Operations:** <10ms

### Throughput

- **Batch Processing:** ~10-20 screenshots/minute (OCR)
- **Batch Processing:** ~2-5 screenshots/minute (Vision)
- **GPT-4 Rate Limits:** Depends on Azure quota

### Resource Usage

- **Memory:** ~200MB base + ~500MB per vision model
- **Disk:** Minimal (configuration and logs)
- **Network:** Azure API calls only (remote mode)

---

## Security Considerations

### File System Access

- ✅ All access mediated through MCP server
- ✅ Subprocess isolation
- ✅ No direct file system access from agent
- ✅ Configurable base directories

### API Keys

- ✅ Environment variables (not in code)
- ✅ Azure DefaultAzureCredential support
- ✅ No keys in logs or outputs

### Data Privacy

- **Local Mode:** All processing on-device (no network)
- **Remote Mode:** Screenshots sent to Azure OpenAI for analysis
- **Configurable:** Users can choose based on privacy needs

---

## Future Enhancements

### Potential Improvements

1. **Additional Tools:**
   - Search screenshots by content
   - Tag management
   - Duplicate detection
   - Metadata extraction

2. **Performance:**
   - Parallel batch processing
   - Tool call batching
   - Connection pooling

3. **Intelligence:**
   - Custom category training
   - User preference learning
   - Smart filename templates

4. **Integration:**
   - VS Code extension
   - Web interface
   - Mobile app

---

## References

- [Microsoft Agent Framework Documentation](https://github.com/microsoft/agent-framework)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Azure OpenAI Documentation](https://learn.microsoft.com/azure/ai-services/openai/)
- [Project Specification](specs/001-screenshot-organizer/spec.md)
- [Project Constitution](.specify/memory/constitution.md)

---

## Glossary

- **Agent:** AI system that can use tools to accomplish tasks
- **Agent Framework:** Microsoft's SDK for building AI agents
- **MCP:** Model Context Protocol - standardized tool interface
- **Tool:** Function that an agent can call to perform operations
- **Thread:** Conversation state/history
- **Orchestration:** Agent's process of calling multiple tools to complete a task
- **Stdio Transport:** Communication via standard input/output streams
- **OCR:** Optical Character Recognition - extracting text from images
- **Vision Model:** AI model that understands image content

---

**Document Version:** 1.0
**Last Updated:** 2025-11-12
**Maintained By:** Screenshot Organizer Project Team
