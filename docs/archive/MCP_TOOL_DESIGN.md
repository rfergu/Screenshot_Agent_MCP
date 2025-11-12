# MCP Tool Design for Agent Framework Integration

**Date:** 2025-11-12
**Purpose:** Design low-level file operation tools for MCP server that Agent Framework will orchestrate

---

## Architecture Overview

```
User: "organize my screenshots"
  ↓
Agent Framework (GPT-4 or Phi-3.5)
  ├─ Understands intent
  ├─ Calls MCP: list_screenshots("/Users/foo/Downloads")
  ├─ For each file:
  │   ├─ Calls MCP: analyze_screenshot(file_path)
  │   ├─ Decides category (using GPT-4's intelligence)
  │   ├─ Calls MCP: create_category_folder(category)
  │   └─ Calls MCP: move_screenshot(file_path, dest_folder)
  └─ Reports results to user
         ↓
    MCP Server (stdio transport)
         ↓
    File System Operations
```

**Key Principle:** Agent Framework = Brain (decisions), MCP Server = Hands (file operations)

---

## MCP Tool Set Design

### 1. **list_screenshots**

**Purpose:** Get list of screenshot files in a directory

**Signature:**
```python
def list_screenshots(
    directory: str,
    recursive: bool = False,
    max_files: Optional[int] = None
) -> Dict[str, Any]:
    """List screenshot files in a directory.

    Args:
        directory: Absolute path to directory to scan
        recursive: Whether to scan subdirectories
        max_files: Maximum number of files to return (optional)

    Returns:
        {
            "files": [
                {
                    "path": "/absolute/path/to/file.png",
                    "filename": "file.png",
                    "size_bytes": 12345,
                    "modified_time": "2025-11-12T10:30:00"
                },
                ...
            ],
            "total_count": 42,
            "truncated": false  # true if max_files limit reached
        }
    """
```

**Why Low-Level:** Just lists files, doesn't analyze them. Agent decides what to do with the list.

---

### 2. **analyze_screenshot**

**Purpose:** Analyze a single screenshot using OCR or vision model

**Signature:**
```python
def analyze_screenshot(
    file_path: str,
    force_vision: bool = False
) -> Dict[str, Any]:
    """Analyze screenshot content using tiered OCR → keyword → vision approach.

    Args:
        file_path: Absolute path to screenshot file
        force_vision: Skip OCR and use vision model directly

    Returns:
        {
            "extracted_text": "text from screenshot...",
            "processing_method": "ocr" | "vision",
            "processing_time_ms": 123.45,
            "vision_description": "optional vision model description",
            "success": true,
            "error": null
        }
    """
```

**Note:** This returns RAW analysis data. The **Agent** decides the category, not the tool.

**Why Changed:** Current version returns `category` and `suggested_filename` - that's the agent's job! This tool should just extract information.

---

### 3. **categorize_screenshot**

**Purpose:** Use keyword classifier to suggest category (fallback for when GPT-4 isn't available)

**Signature:**
```python
def categorize_screenshot(
    text: str,
    available_categories: List[str]
) -> Dict[str, Any]:
    """Suggest category based on text content using keyword matching.

    Args:
        text: Extracted text from screenshot
        available_categories: List of valid category names

    Returns:
        {
            "suggested_category": "code",
            "confidence": 0.85,
            "matched_keywords": ["def", "import", "python"],
            "method": "keyword_classifier"
        }
    """
```

**Why Separate:** Agent can choose to use GPT-4's intelligence OR fall back to simple keyword matching.

---

### 4. **get_categories**

**Purpose:** Get list of available/configured categories

**Signature:**
```python
def get_categories() -> Dict[str, Any]:
    """Get list of available screenshot categories.

    Returns:
        {
            "categories": [
                {
                    "name": "code",
                    "description": "Code snippets, terminal output, IDE screenshots",
                    "keywords": ["def", "class", "import", "function"]
                },
                {
                    "name": "errors",
                    "description": "Error messages, stack traces, warnings",
                    "keywords": ["error", "exception", "traceback"]
                },
                ...
            ],
            "default_category": "other"
        }
    """
```

**Why Needed:** Agent needs to know valid categories before categorizing.

---

### 5. **create_category_folder**

**Purpose:** Create a folder for organizing screenshots

**Signature:**
```python
def create_category_folder(
    category: str,
    base_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Create a category folder for organizing screenshots.

    Args:
        category: Category name (e.g., "code", "errors")
        base_dir: Base directory for organization (optional, uses config default)

    Returns:
        {
            "folder_path": "/Users/foo/Screenshots/organized/code",
            "created": true,  # false if already existed
            "success": true
        }
    """
```

**Why Low-Level:** Just creates a folder. Agent decides WHEN to create it.

---

### 6. **move_screenshot**

**Purpose:** Move a screenshot file to a destination folder with optional renaming

**Signature:**
```python
def move_screenshot(
    source_path: str,
    dest_folder: str,
    new_filename: Optional[str] = None,
    keep_original: bool = True
) -> Dict[str, Any]:
    """Move (or copy) a screenshot file to a destination folder.

    Args:
        source_path: Absolute path to source file
        dest_folder: Absolute path to destination folder
        new_filename: Optional new filename (if None, keeps original name)
        keep_original: If true, copy instead of move

    Returns:
        {
            "original_path": "/Users/foo/Downloads/screenshot.png",
            "new_path": "/Users/foo/Screenshots/organized/code/auth_bug_2025-11-12.png",
            "operation": "copy" | "move",
            "success": true
        }
    """
```

**Why Low-Level:** Just moves files. Agent decides the destination and new filename.

---

### 7. **generate_filename**

**Purpose:** Generate a descriptive filename based on content analysis

**Signature:**
```python
def generate_filename(
    original_filename: str,
    category: str,
    text: Optional[str] = None,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """Generate a descriptive filename for a screenshot.

    Args:
        original_filename: Original file name
        category: Category name
        text: Optional extracted text (first few words used)
        description: Optional description from vision model

    Returns:
        {
            "suggested_filename": "auth_error_login_page_2025-11-12.png",
            "extension": ".png",
            "timestamp": "2025-11-12"
        }
    """
```

**Why Separate:** Agent can use GPT-4 to generate better filenames OR use this simple utility.

---

## Tool Comparison: Current vs Proposed

### Current High-Level Tools (❌ Too Smart)

**Current `analyze_screenshot`:**
```python
Returns: {
    "category": "code",              # ← MCP decides category (too smart!)
    "suggested_filename": "foo.png",  # ← MCP decides filename (too smart!)
    "extracted_text": "...",
    "processing_method": "ocr"
}
```
**Problem:** MCP server is making categorization decisions. That should be the **Agent's** job!

**Current `batch_process`:**
```python
# Processes ALL files, categorizes them, generates stats
# This is what the AGENT should orchestrate, not a single tool!
```
**Problem:** This is agent orchestration logic in a tool. Agent Framework should control the loop.

---

### Proposed Low-Level Tools (✅ Agent Orchestrates)

**Proposed `analyze_screenshot`:**
```python
Returns: {
    "extracted_text": "...",        # ← Just the facts
    "processing_method": "ocr",      # ← Just the facts
    "vision_description": "..."      # ← Just the facts
}
```
**Agent Decides:** Category, filename, what to do next

**Agent Orchestrates Batch:**
```python
# Agent Framework does:
files = mcp_client.list_screenshots("/path")
for file in files:
    analysis = mcp_client.analyze_screenshot(file.path)
    category = agent_decides_category(analysis)  # ← GPT-4 intelligence!
    mcp_client.create_category_folder(category)
    new_name = agent_generates_filename(analysis, category)  # ← GPT-4 creativity!
    mcp_client.move_screenshot(file.path, category_folder, new_name)
```
**Result:** Agent has full control, can use GPT-4's intelligence for decisions

---

## Agent Framework Integration

### How Agent Framework Will Use MCP Tools

**1. Agent Client Creates MCP Connection:**
```python
# In agent_client.py
from mcp.client import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class AgentClient:
    def __init__(self):
        # Start MCP server as subprocess
        self.mcp_server_params = StdioServerParameters(
            command="python",
            args=["-m", "src", "server"]
        )

        # MCP session will be created in async context
        self.mcp_session = None

    async def start_mcp_session(self):
        """Initialize MCP client session."""
        self.mcp_read, self.mcp_write = await stdio_client(self.mcp_server_params).__aenter__()
        self.mcp_session = await ClientSession(self.mcp_read, self.mcp_write).__aenter__()
        await self.mcp_session.initialize()
```

**2. Create Tool Wrapper Functions:**
```python
# In agent_client.py or new mcp_client_wrapper.py

async def list_screenshots_tool(directory: str, recursive: bool = False):
    """Tool wrapper that calls MCP server."""
    result = await mcp_session.call_tool(
        "list_screenshots",
        {"directory": directory, "recursive": recursive}
    )
    return json.loads(result.content[0].text)

async def analyze_screenshot_tool(file_path: str, force_vision: bool = False):
    """Tool wrapper that calls MCP server."""
    result = await mcp_session.call_tool(
        "analyze_screenshot",
        {"file_path": file_path, "force_vision": force_vision}
    )
    return json.loads(result.content[0].text)

# ... more wrappers for each MCP tool
```

**3. Register Tools with Agent Framework:**
```python
# In agent_client.py

from agent_framework import ChatAgent, Tool

# Remote mode (GPT-4) - HAS TOOLS
if mode == "remote":
    tools = [
        Tool(
            name="list_screenshots",
            description="List screenshot files in a directory",
            function=list_screenshots_tool,
            parameters={...}
        ),
        Tool(
            name="analyze_screenshot",
            description="Analyze a screenshot using OCR or vision",
            function=analyze_screenshot_tool,
            parameters={...}
        ),
        # ... all MCP tools
    ]

    agent = ChatAgent(
        chat_client=azure_chat_client,
        tools=tools  # ← Tools available
    )

# Local mode (Phi-3.5) - NO TOOLS
else:
    agent = ChatAgent(
        chat_client=foundry_chat_client,
        tools=[]  # ← No tools, just chat
    )
```

**4. Agent Instructions Updated:**
```python
agent_instructions = """
You are a screenshot organization assistant with access to file system operations.

Available Tools:
- list_screenshots: List screenshot files in a directory
- analyze_screenshot: Analyze a screenshot's content (OCR/vision)
- get_categories: Get available category types
- categorize_screenshot: Suggest category based on keywords (fallback)
- create_category_folder: Create a folder for organizing
- move_screenshot: Move a file to a folder
- generate_filename: Generate descriptive filename (fallback)

When a user asks to organize screenshots:
1. Use list_screenshots to find files
2. For each file:
   a. Use analyze_screenshot to extract content
   b. Intelligently decide the category based on content
   c. Use create_category_folder if needed
   d. Generate a descriptive filename
   e. Use move_screenshot to organize
3. Report progress and results

Use your intelligence to make smart categorization decisions!
"""
```

---

## Mode Comparison

### Remote Mode (GPT-4) - FULL TOOLS
```
User: "organize my screenshots in ~/Downloads"
  ↓
GPT-4 (via Agent Framework):
  1. Calls list_screenshots("~/Downloads")
     → Returns: [file1.png, file2.png, file3.png]

  2. Calls analyze_screenshot("file1.png")
     → Returns: {text: "def login()...", method: "ocr"}

  3. GPT-4 DECIDES: "This is code, category should be 'code'"

  4. Calls create_category_folder("code")
     → Returns: {folder_path: "~/Screenshots/organized/code"}

  5. GPT-4 CREATES: "Filename should be login_function_2025-11-12.png"

  6. Calls move_screenshot("file1.png", "~/Screenshots/organized/code", "login_function_2025-11-12.png")
     → Returns: {success: true}

  (Repeats for file2, file3...)

  7. Reports: "I organized 3 screenshots: 2 code, 1 error"
```

**Key:** GPT-4's intelligence makes categorization and naming decisions

---

### Local Mode (Phi-3.5) - NO TOOLS
```
User: "organize my screenshots in ~/Downloads"
  ↓
Phi-3.5 (via Agent Framework):
  "I understand you want to organize screenshots. However, I'm running in
  local test mode without file system access. To actually organize files,
  please use remote mode with: python -m src chat --mode remote

  I can help you understand how the organization process would work though!"
```

**Key:** Same agent code, just no tools available

---

## Implementation Plan

### Phase 1: Update MCP Server Tools ✅

**Files to modify:**
- `src/mcp_tools.py` - Update tool implementations
- `src/screenshot_mcp_server.py` - Register new tools

**Changes:**
1. Modify `analyze_screenshot` to return raw analysis (no category/filename)
2. Add `list_screenshots` tool
3. Add `get_categories` tool
4. Add `categorize_screenshot` tool (keyword fallback)
5. Add `create_category_folder` tool
6. Rename `organize_file` → `move_screenshot` and simplify
7. Add `generate_filename` tool (simple utility)
8. Remove `batch_process` (agent will orchestrate this)

---

### Phase 2: Create MCP Client Wrapper ✅

**New file:** `src/mcp_client_wrapper.py`

**Purpose:** Wrapper that makes MCP tools available to Agent Framework

**Functions:**
- `start_mcp_server()` - Start MCP server subprocess
- `create_mcp_session()` - Initialize MCP client session
- `get_mcp_tools()` - Return Agent Framework Tool objects
- Individual tool wrapper functions

---

### Phase 3: Integrate into Agent Client ✅

**Files to modify:**
- `src/agent_client.py` - Use MCP client instead of direct tools

**Changes:**
1. Initialize MCP client session
2. Get MCP tools if in remote mode
3. Pass tools to ChatAgent
4. Update agent instructions for tool orchestration

---

### Phase 4: Update Agent Instructions ✅

**Files to modify:**
- `src/agent_client.py` - Update system prompt

**Changes:**
- Explain available MCP tools
- Provide orchestration patterns
- Emphasize agent's decision-making role

---

### Phase 5: Testing ✅

**Test Scenarios:**

1. **Remote mode with GPT-4:**
   - User: "organize screenshots in ~/Downloads"
   - Verify: GPT-4 calls MCP tools intelligently
   - Verify: Files are categorized and moved

2. **Local mode with Phi-3.5:**
   - User: "organize screenshots in ~/Downloads"
   - Verify: Agent explains tools not available
   - Verify: No errors, graceful message

3. **MCP test client:**
   - Verify: MCP server still works standalone
   - Verify: Can call tools directly

---

## Success Criteria

### ✅ Agent Framework Integration
- [ ] Agent Framework connects to MCP server
- [ ] Tools are available in remote mode
- [ ] Tools are NOT available in local mode
- [ ] Agent code identical for both modes

### ✅ File System Access via MCP
- [ ] All file operations go through MCP protocol
- [ ] Agent never touches file system directly
- [ ] MCP server mediates all I/O

### ✅ Intelligent Orchestration
- [ ] GPT-4 makes categorization decisions
- [ ] GPT-4 generates descriptive filenames
- [ ] GPT-4 controls workflow (list → analyze → categorize → move)
- [ ] MCP tools are "dumb" (just do what they're told)

### ✅ Mode Consistency
- [ ] Same agent code for local and remote
- [ ] Local mode: conversation only (no tools)
- [ ] Remote mode: full capabilities (with tools)
- [ ] Clear user messaging about mode differences

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     USER REQUEST                             │
│          "Organize my screenshots in ~/Downloads"           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              AGENT FRAMEWORK (Orchestrator)                  │
│                                                              │
│  ┌──────────────────────────────────────────────┐          │
│  │  ChatAgent                                    │          │
│  │  ├─ Chat Client: GPT-4 or Phi-3.5            │          │
│  │  ├─ Tools: MCP Client (if remote mode)       │          │
│  │  └─ Instructions: Orchestration patterns     │          │
│  └──────────────────────────────────────────────┘          │
│                                                              │
│  Decision Making (GPT-4 Intelligence):                      │
│  • Which files to process?                                  │
│  • What category for each file?                             │
│  • What filename to use?                                    │
│  • When to create folders?                                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
                   (stdio transport)
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    MCP SERVER (Tool Provider)                │
│                                                              │
│  Tools (File Operations):                                   │
│  ├─ list_screenshots(dir)        → List files              │
│  ├─ analyze_screenshot(path)     → Extract content         │
│  ├─ get_categories()             → Get category list       │
│  ├─ categorize_screenshot(text)  → Keyword matching        │
│  ├─ create_category_folder(cat)  → Create folder           │
│  ├─ move_screenshot(src, dest)   → Move file               │
│  └─ generate_filename(...)       → Simple filename gen     │
│                                                              │
│  Note: MCP tools are "dumb" - they just execute operations │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      FILE SYSTEM                             │
│                                                              │
│  ~/Downloads/                                               │
│  ├─ screenshot1.png                                         │
│  ├─ screenshot2.png                                         │
│  └─ screenshot3.png                                         │
│                                                              │
│  ~/Screenshots/organized/                                   │
│  ├─ code/                                                   │
│  │   └─ login_function_2025-11-12.png                      │
│  ├─ errors/                                                 │
│  │   └─ auth_error_2025-11-12.png                          │
│  └─ other/                                                  │
│      └─ misc_screenshot_2025-11-12.png                      │
└─────────────────────────────────────────────────────────────┘
```

**Key Insight:**
- **Brain (Agent Framework + GPT-4):** Makes intelligent decisions
- **Hands (MCP Server):** Performs file operations as instructed
- **Clear separation of concerns**

---

## Next Steps

1. Start with Phase 1: Update MCP server tools
2. Create tool design document for review
3. Implement new/modified tools
4. Test MCP server with updated tools
5. Proceed to Phase 2: MCP client wrapper
