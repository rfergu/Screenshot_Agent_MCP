# Screenshot Organizer with Local AI - Feature Specification

## Feature Name
Screenshot Organizer with Local AI Processing

## Feature Description
A terminal-based tool that intelligently organizes screenshots using local AI models (OCR and Phi-3 Vision), with GPT-4 orchestrating the conversation through MCP protocol. The system prioritizes local processing to maintain privacy and minimize costs.

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
- GPT-4 understands natural language requests
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
- Reports cost savings by using local processing
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

### FR-004: MCP Server Implementation
- Implement three MCP tools:
  1. analyze_screenshot(path, force_vision=False)
  2. batch_process(folder)
  3. organize_file(source, category, new_name)
- Follow MCP protocol specifications
- Return structured JSON responses

### FR-005: File Management
- Create organized folder structure
- Support common image formats (PNG, JPG, JPEG, GIF, BMP)
- Generate descriptive filenames (no spaces, filesystem-safe)
- Handle duplicate filenames gracefully

### FR-006: GPT-4 Integration
- Use GPT-4 for natural language understanding
- Orchestrate MCP tool calls based on user intent
- Provide conversational responses
- Maintain session context

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

## Non-Functional Requirements

### NFR-001: Performance
- OCR processing: <50ms per image
- Vision processing: <2s per image
- Batch processing: Linear scaling with file count

### NFR-002: Privacy
- No image data sent to external services
- All vision processing done locally
- Only text metadata sent to GPT-4

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
- [ ] All user stories have clear acceptance criteria
- [ ] Functional requirements are testable
- [ ] Non-functional requirements are measurable
- [ ] Privacy requirements are explicitly stated
- [ ] Performance targets are defined
- [ ] Error handling is comprehensive
- [ ] File organization structure is clear
- [ ] Integration points are well-defined

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

### Pending Clarifications
- Exact format for renamed files (timestamp prefix?)
- Maximum batch size limitations
- Configuration file format and location
- Logging verbosity levels and output destination