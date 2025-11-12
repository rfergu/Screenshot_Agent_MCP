# Screenshot Organizer with Local AI - Feature Specification

## Feature Name
Screenshot Organizer with Local AI Processing

## Feature Description
A terminal-based tool that intelligently organizes screenshots using local AI models (OCR and Phi-3 Vision), with Azure AI (Foundry or Azure OpenAI) orchestrating the conversation through Microsoft Agent Framework. The system uses embedded tool functions for screenshot processing and prioritizes local processing to maintain privacy and minimize costs.

## User Stories

### US-001: Analyze Single Screenshot
**As a** user with many unorganized screenshots  
**I want to** analyze a single screenshot file  
**So that** I can understand its content and get it properly categorized  

**Acceptance Criteria:**
- System attempts OCR first for text extraction
- If OCR yields >10 words, uses keyword-based classification
- If OCR yields <10 words, uses local Phi-3 Vision model
- Returns category (code/errors/documentation/design/communication/memes/other)
- Suggests descriptive filename based on content
- Reports processing method used and time taken
- Never sends image data to external APIs

### US-002: Batch Process Screenshots
**As a** user with a folder full of screenshots  
**I want to** process all screenshots in a folder at once  
**So that** I can organize my entire screenshot collection efficiently  

**Acceptance Criteria:**
- Processes all image files in specified folder
- Shows progress indicator during processing
- Reports count of files processed by each method (OCR vs Vision)
- Displays total processing time and per-file average
- Handles errors gracefully without stopping batch
- Creates organized folder structure if it doesn't exist

### US-003: Interactive Chat Interface
**As a** user
**I want to** interact with the tool through natural language
**So that** I can easily organize screenshots without memorizing commands

**Acceptance Criteria:**
- Azure AI models (via Foundry or Azure OpenAI) understand natural language requests
- Provides helpful suggestions and clarifications
- Explains what the tool is doing at each step
- Offers to process individual files or batches
- Remembers context within a session
- Provides clear error messages when something fails

### US-004: Organize and Rename Files
**As a** user  
**I want to** have my screenshots automatically moved and renamed  
**So that** I can easily find them later  

**Acceptance Criteria:**
- Creates organized folder structure (code/errors/documentation/design/communication/memes/other)
- Moves files to appropriate category folders
- Renames files with descriptive names based on content
- Handles filename conflicts (appends numbers if needed)
- Preserves original file metadata
- Optionally keeps originals in an archive folder

### US-005: View Processing Metrics
**As a** user  
**I want to** see performance metrics for processing  
**So that** I understand how the tool is performing  

**Acceptance Criteria:**
- Shows processing method (OCR or Vision) for each file
- Displays processing time per file
- Shows batch statistics (files per method, total time)
- Reports cost savings by using local processing (only metadata sent to Azure AI)
- Indicates when vision model is downloading/loading

## Functional Requirements

### FR-001: OCR Processing
- Must use Tesseract OCR as first processing attempt
- Extract text from screenshots
- Count words to determine if sufficient for classification
- Process text-heavy screenshots in <50ms

### FR-002: Vision Model Processing
- Use Phi-3 Vision MLX for visual analysis
- Only triggered when OCR yields insufficient text (<10 words)
- Process visual content in <2 seconds
- Auto-download model on first use (~8GB)

### FR-003: Classification Logic
- Implement keyword-based classification for OCR results
- Categories: code, errors, documentation, design, communication, memes, other
- Classification rules:
  - code: Contains "def", "function", "import", "class", "const", "var"
  - errors: Contains "error", "exception", "failed", "traceback"
  - documentation: Contains "install", "usage", "api", "guide", "readme"
  - communication: Contains "sent", "replied", "message", "@"
  - other: Default if no patterns match

### FR-004: Tool Function Implementation
- Implement three tool functions as standalone Python functions with Pydantic type annotations:
  1. `analyze_screenshot(path, force_vision=False)` - Analyze single screenshot
  2. `batch_process(folder, recursive, max_files, organize)` - Process folder of screenshots
  3. `organize_file(source_path, category, new_filename, archive_original, base_path)` - Organize and rename file
- Use `Annotated[type, Field(description="...")]` pattern for automatic tool discovery
- Tools embedded directly in Agent Framework (no separate MCP server process)
- Return structured dictionary responses

### FR-005: File Management
- Create organized folder structure
- Support common image formats (PNG, JPG, JPEG, GIF, BMP)
- Generate descriptive filenames (no spaces, filesystem-safe)
- Handle duplicate filenames gracefully

### FR-006: Azure AI Integration (Foundry or Azure OpenAI)
- Use **Microsoft Agent Framework** for AI orchestration
- Support **either** Azure AI Foundry serverless endpoints **or** Azure OpenAI resource endpoints
- Automatically detect endpoint type via `AzureOpenAIChatClient`:
  - AI Foundry: `https://xxx.services.ai.azure.com/api/projects/xxx`
  - Azure OpenAI: `https://xxx.cognitiveservices.azure.com`
- Use Azure models (GPT-4, GPT-4o, etc.) for natural language understanding
- Agent Framework automatically orchestrates tool calls based on user intent
- Provide conversational responses via `ChatAgent`
- Maintain session context using `AgentThread` serialization
- Authentication support:
  - Azure OpenAI: API key required
  - AI Foundry: API key or Azure CLI authentication (DefaultAzureCredential)

### FR-007: Error Handling
- Gracefully handle OCR failures
- Provide fallback when vision model fails
- Report clear error messages to users
- Continue batch processing despite individual failures

### FR-008: Performance Monitoring
- Track processing time per file
- Count files processed by each method
- Calculate and display aggregate statistics
- Show cost savings from local processing

### FR-009: Microsoft Agent Framework Implementation
- Use `agent-framework` Python package (>=0.1.0)
- Create `ChatAgent` with embedded tool functions (not separate MCP server)
- Use `AzureOpenAIChatClient` for dual endpoint support (Foundry + Azure OpenAI)
- Implement async conversation pattern with `await agent.run()`
- Use `AgentThread` for conversation state management:
  - `agent.get_new_thread()` for new conversations
  - `await thread.serialize()` for session persistence
  - `await agent.deserialize_thread()` for session restoration
- Tools provided as list to `ChatAgent(tools=[analyze_screenshot, batch_process, organize_file])`
- Agent Framework handles:
  - Automatic tool discovery via type annotations
  - Tool call orchestration (no manual loops)
  - Message formatting and API calls
  - Thread state management

## Non-Functional Requirements

### NFR-001: Performance
- OCR processing: <50ms per image
- Vision processing: <2s per image
- Batch processing: Linear scaling with file count

### NFR-002: Privacy
- No image data sent to external services
- All vision processing done locally
- Only text metadata sent to Azure AI (Foundry or Azure OpenAI) for orchestration

### NFR-003: Usability
- Clear command-line interface
- Helpful error messages
- Progress indicators for long operations
- Natural language interaction

### NFR-004: Reliability
- 90%+ successful categorization rate
- Graceful degradation on failures
- Robust error handling
- Consistent file organization

## Review & Acceptance Checklist
- [x] All user stories have clear acceptance criteria
- [x] Functional requirements are testable
- [x] Non-functional requirements are measurable
- [x] Privacy requirements are explicitly stated
- [x] Performance targets are defined
- [x] Error handling is comprehensive
- [x] File organization structure is clear
- [x] Integration points are well-defined
- [x] Microsoft Agent Framework integration specified
- [x] Tool function architecture defined
- [x] Dual Azure endpoint support documented

## Open Questions & Clarifications

### Clarified Items
1. **Q: Should we keep original files after organizing?**
   A: Optional - user can choose to archive originals

2. **Q: How to handle non-image files in batch processing?**
   A: Skip with warning message, continue processing

3. **Q: What if Phi-3 Vision model fails to download?**
   A: Fall back to basic keyword classification from OCR

4. **Q: How to handle very large images?**
   A: Resize for processing while maintaining aspect ratio

5. **Q: Why use Microsoft Agent Framework instead of standalone MCP server?**
   A: Embedded tools provide:
   - Simpler architecture (no separate server process)
   - Lower latency (direct function calls, no IPC overhead)
   - Easier testing and debugging
   - Built-in thread persistence and tool orchestration
   - Still demonstrates clear tool abstraction through function interface
   - Future-ready for multi-agent patterns

### Pending Clarifications
- Exact format for renamed files (timestamp prefix?)
- Maximum batch size limitations
- Configuration file format and location
- Logging verbosity levels and output destination