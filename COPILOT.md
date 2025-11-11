# Screenshot Organizer Project - AI Agent Context

## Current Project State
- **Phase:** Specification Complete, Ready for Implementation
- **Feature Branch:** 001-screenshot-organizer
- **Last Updated:** Initial specification

## Project Overview
You are building a terminal-based screenshot organization tool that uses local AI models (Tesseract OCR and Phi-3 Vision MLX) to intelligently categorize and rename screenshots. The system prioritizes privacy by processing everything locally, with only GPT-4 used for natural language orchestration.

## Key Design Decisions Made
1. **OCR-First Approach:** Always attempt Tesseract OCR before using vision models
2. **Local Processing Only:** No images sent to external APIs, maintaining complete privacy
3. **MCP Protocol:** Clean separation between chat interface and processing tools
4. **Tiered Processing:** OCR for text-heavy (>10 words), Vision for visual content
5. **Zero Cost:** All image processing is free (local only)

## Architecture Summary
```
User → Chat Client (GPT-4) → MCP Server → Processing Layer (OCR/Vision) → File Organization
```

## Implementation Priorities
1. **Core Functionality First:** Get OCR + classification working
2. **Then Add Vision:** Integrate Phi-3 Vision for visual content
3. **MCP Integration:** Implement protocol and tools
4. **Chat Interface:** Add GPT-4 orchestration
5. **Polish:** Error handling, logging, performance optimization

## Current Tasks
Refer to `specs/001-screenshot-organizer/tasks.md` for the complete implementation breakdown. Start with Phase 1 (Infrastructure Setup) and proceed sequentially.

## Key Files to Reference
- **Constitution:** `.specify/memory/constitution.md` - Core principles and standards
- **Specification:** `specs/001-screenshot-organizer/spec.md` - User stories and requirements
- **Technical Plan:** `specs/001-screenshot-organizer/plan.md` - Implementation details
- **Task List:** `specs/001-screenshot-organizer/tasks.md` - Step-by-step implementation
- **Data Model:** `specs/001-screenshot-organizer/data-model.md` - Data structures
- **Research:** `specs/001-screenshot-organizer/research.md` - Technical decisions
- **API Contract:** `specs/001-screenshot-organizer/contracts/mcp-api-spec.json` - MCP tool definitions

## Critical Implementation Notes

### Performance Requirements
- OCR must process in <50ms
- Vision model must process in <2s
- Batch processing should scale linearly

### Error Handling
- Never crash on single file failure
- Always continue batch processing
- Provide clear error messages
- Log all errors for debugging

### Testing Requirements
- Unit tests for each component
- Integration tests for workflows
- Performance benchmarks
- 80% minimum code coverage

## Dependencies to Install
```bash
# Core requirements
pytesseract==0.3.10
pillow==10.2.0
phi-3-vision-mlx==0.1.0
openai==1.12.0
mcp==0.1.0
rich==13.7.0
click==8.1.7
pydantic==2.5.0
python-dotenv==1.0.0
```

## System Dependencies
- Tesseract OCR (system install required)
- Python 3.10+ (for Phi-3 Vision MLX)
- ~8GB disk space for Phi-3 Vision model

## File Organization Structure
```
~/Screenshots/organized/
├── code/
├── errors/
├── documentation/
├── design/
├── communication/
├── memes/
└── other/
```

## MCP Tools to Implement
1. `analyze_screenshot(path, force_vision=False)` - Main analysis tool
2. `batch_process(folder, recursive=False, max_files=None, organize=False)` - Batch processing
3. `organize_file(source_path, category, new_filename, archive_original=False)` - File organization

## Classification Keywords
- **code:** def, function, import, class, const, var, return, if, for
- **errors:** error, exception, failed, traceback, warning, fatal
- **documentation:** install, usage, api, guide, readme, tutorial, docs
- **communication:** sent, replied, message, @, from:, to:, subject:
- **design:** figma, sketch, wireframe, mockup, ui, ux, design
- **memes:** meme, funny, lol, 😂, 🤣

## Success Metrics
- 90%+ successful categorization rate
- $0.00 cost per image processed
- <50ms OCR processing time
- <2s vision processing time
- Natural conversation flow with users

## Next Implementation Steps
1. Create project structure and install dependencies
2. Implement OCR processor with text extraction
3. Add keyword-based classification
4. Integrate Phi-3 Vision for visual content
5. Build MCP server with three tools
6. Create GPT-4 orchestrated chat interface
7. Add batch processing capabilities
8. Implement file organization logic
9. Add comprehensive error handling
10. Create test suite and documentation

## Questions to Clarify (if any)
- Exact filename format (consider adding timestamp?)
- Maximum batch size limitations
- Logging verbosity preferences
- Configuration file location

## Remember
- **Always prioritize local processing** for privacy and cost
- **Follow the constitution** for code quality and standards
- **Test each component** before moving to the next
- **Keep the user informed** with clear progress indicators
- **Handle errors gracefully** without stopping batch operations

You have all the specifications needed to implement this project. Follow the task breakdown in order and refer to the research document for technical decisions. Good luck with the implementation!