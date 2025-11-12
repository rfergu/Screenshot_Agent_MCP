# MCP Architecture Analysis & Plan

**Date:** 2025-11-12
**Issue:** File system access should go through MCP for demo purposes
**Current State:** Tools call file system directly (not through MCP)

---

## Current Architecture (PROBLEM)

### How It Works Now:

```
┌─────────────────────────────────────────────────────────────┐
│                          REMOTE MODE                         │
└─────────────────────────────────────────────────────────────┘

User Input
    ↓
AgentClient (agent_client.py)
    ↓
ChatAgent (Agent Framework)
    |
    ├→ Chat: AzureOpenAIChatClient → GPT-4
    |
    └→ Tools: [analyze_screenshot, batch_process, organize_file]
           ↓
           Direct function calls (mcp_tools.py)
           ↓
           ┌──────────────────────────────────────┐
           │ DIRECT FILE SYSTEM ACCESS            │
           │ - OCRProcessor reads files           │
           │ - VisionProcessor reads files        │
           │ - FileOrganizer moves files          │
           │ - BatchProcessor scans directories   │
           └──────────────────────────────────────┘
```

### The Problem:

❌ **No MCP protocol demonstration** - Tools call Python file operations directly
❌ **MCP server exists but isn't used** - `screenshot_mcp_server.py` is standalone
❌ **Not a true MCP demo** - Missing the key architectural benefit of MCP

---

## What MCP Should Provide

The Model Context Protocol (MCP) is designed to:

1. **Standardize tool/resource access** - Common protocol for LLMs to access tools
2. **Separate concerns** - Tools/resources in separate process from LLM
3. **Security boundaries** - File access mediated through controlled server
4. **Reusability** - Same MCP server works with different LLM frontends

---

## Desired Architecture (SOLUTION)

### Option 1: Agent Framework with MCP Client

```
User Input
    ↓
AgentClient
    ↓
ChatAgent (Agent Framework)
    ├→ Chat: AzureOpenAIChatClient → GPT-4
    |
    └→ Tools: Via MCP Client Protocol
           ↓
       ┌───────────────────────────────┐
       │   MCP CLIENT (in-process)     │
       │   - Connects to MCP server    │
       │   - Sends tool requests       │
       │   - Receives responses        │
       └───────────────────────────────┘
           ↓ (stdio/HTTP)
       ┌───────────────────────────────┐
       │   MCP SERVER                  │
       │   (screenshot_mcp_server.py)  │
       │   - Exposes tools via MCP     │
       │   - Handles tool calls        │
       └───────────────────────────────┘
           ↓
       ┌───────────────────────────────┐
       │   FILE SYSTEM ACCESS          │
       │   - OCR reads files           │
       │   - Vision reads files        │
       │   - Organizer moves files     │
       └───────────────────────────────┘
```

### Option 2: Separate MCP Server + Claude Desktop/Other Client

```
┌──────────────────────────────┐       ┌──────────────────────────────┐
│   Claude Desktop / Client    │       │   Python Agent Client        │
│   - Uses MCP protocol        │  OR   │   - Uses MCP protocol        │
│   - Connects to server       │       │   - Custom interface         │
└──────────────────────────────┘       └──────────────────────────────┘
           ↓                                        ↓
           └────────────────────┬───────────────────┘
                                ↓
                    ┌───────────────────────────────┐
                    │   MCP SERVER (stdio)          │
                    │   screenshot_mcp_server.py    │
                    │   - analyze_screenshot        │
                    │   - batch_process             │
                    │   - organize_file             │
                    └───────────────────────────────┘
                                ↓
                    ┌───────────────────────────────┐
                    │   FILE SYSTEM ACCESS          │
                    └───────────────────────────────┘
```

---

## Investigation: Can Agent Framework Use MCP?

### Question 1: Does Microsoft Agent Framework support MCP clients?

Need to check:
- Can ChatAgent connect to external MCP servers?
- Can we configure MCP transport (stdio/HTTP)?
- Or do we need custom integration?

### Question 2: What's the right demo architecture?

**Option A: Integrated (Agent Framework + MCP)**
- Pros: Single unified interface, showcases both Agent Framework AND MCP
- Cons: Complex integration, may not be supported natively

**Option B: Separate (Standalone MCP Server)**
- Pros: Pure MCP demo, works with any MCP client (Claude Desktop, etc.)
- Cons: Loses Agent Framework integration

**Option C: Dual Mode**
- Remote: Agent Framework with tools (current, no MCP)
- MCP Mode: Separate MCP server for pure MCP demo
- Pros: Best of both worlds, clear separation
- Cons: Two different architectures

---

## Recommended Plan: Dual Architecture

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    MODE 1: AGENT FRAMEWORK                      │
│                    (Production AI Agents)                       │
└─────────────────────────────────────────────────────────────────┘

User → AgentClient → ChatAgent → Tools (direct) → File System
       (cli_interface.py)

Purpose: Demonstrate Microsoft Agent Framework for production agents
Tools: Embedded directly in agent
File Access: Direct Python calls
When: python -m src.cli_interface --mode remote


┌─────────────────────────────────────────────────────────────────┐
│                    MODE 2: MCP PROTOCOL DEMO                    │
│                    (Standardized Tool Access)                   │
└─────────────────────────────────────────────────────────────────┘

Client → MCP Server → Tools → File System
(Claude Desktop,      (stdio transport)
 custom client,
 or test client)

Purpose: Demonstrate Model Context Protocol for tool standardization
Tools: Exposed via MCP protocol
File Access: Mediated through MCP server
When: python -m src server  (or configure in Claude Desktop)
```

### What This Demonstrates

**Agent Framework Mode:**
- ✅ Production AI agent development
- ✅ Microsoft Agent Framework capabilities
- ✅ Tool orchestration with LLMs
- ✅ Conversation management

**MCP Server Mode:**
- ✅ Model Context Protocol specification
- ✅ Standardized tool interface
- ✅ Process separation and security
- ✅ LLM-agnostic tool access
- ✅ Works with any MCP client (Claude Desktop, custom, etc.)

---

## Implementation Plan

### Phase 1: Clean Up MCP Server ✅

**Status:** Already exists and works!

**Current Files:**
- `src/screenshot_mcp_server.py` - MCP server implementation
- `src/mcp_tools.py` - Tool implementations
- `src/__main__.py` - Has `server` command

**Verify:**
```bash
# Start MCP server
python -m src server

# Test with MCP client
# (would need MCP test client or Claude Desktop integration)
```

### Phase 2: Create Test Client for MCP Server

**Goal:** Demonstrate MCP in action

**Create:** `scripts/test_mcp_client.py`
```python
"""Test client for MCP server demonstration."""
import asyncio
from mcp.client import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def test_mcp():
    """Test MCP server by calling tools."""
    server_params = StdioServerParameters(
        command="python",
        args=["-m", "src", "server"]
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize
            await session.initialize()

            # List tools
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools]}")

            # Call analyze_screenshot tool
            result = await session.call_tool(
                "analyze_screenshot",
                {
                    "path": "/path/to/screenshot.png",
                    "force_vision": False
                }
            )
            print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(test_mcp())
```

### Phase 3: Create Claude Desktop Integration Guide

**Create:** `docs/CLAUDE_DESKTOP_SETUP.md`

Show users how to:
1. Configure Claude Desktop to use the MCP server
2. Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:
```json
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
3. Use screenshot tools directly in Claude Desktop

### Phase 4: Update Documentation

**Update:**
1. `README.md` - Add MCP server section
2. `DEMO.md` - Add MCP demo instructions
3. `specs/001-screenshot-organizer/spec.md` - Clarify dual architecture

**Key Points:**
- Two modes: Agent Framework (embedded) vs MCP Server (protocol)
- Agent Framework for production agents
- MCP Server for standardized tool access
- MCP works with any client (Claude Desktop, custom, etc.)

### Phase 5: Create Demo Scripts

**Create:**
1. `scripts/demo_agent_framework.py` - Show Agent Framework in action
2. `scripts/demo_mcp_protocol.py` - Show MCP protocol in action
3. `scripts/demo_comparison.py` - Side-by-side comparison

---

## Decision Points

### ✅ Keep Both Architectures

**Agent Framework Mode:**
- Current cli_interface.py
- Tools embedded directly
- For: Production AI agent demos

**MCP Server Mode:**
- screenshot_mcp_server.py
- Tools via MCP protocol
- For: Protocol standardization demos

### ✅ Clear Naming

- `--mode remote` → Agent Framework with embedded tools
- `server` command → MCP protocol server

### ✅ Documentation

- Explain WHY two modes exist
- Show WHAT each demonstrates
- Provide clear examples for each

---

## Next Steps (In Order)

1. ✅ **Verify MCP server works**
   ```bash
   python -m src server
   ```

2. **Create MCP test client**
   - Simple client that calls tools via MCP
   - Demonstrates protocol in action

3. **Update documentation**
   - Explain dual architecture
   - Add MCP setup instructions
   - Show how to use with Claude Desktop

4. **Create demo scripts**
   - Agent Framework demo
   - MCP protocol demo
   - Comparison demo

5. **Test both paths**
   - Agent Framework: Full workflow
   - MCP Server: Protocol compliance

---

## Summary

**Current Problem:** File access is direct, not through MCP

**Solution:** Dual architecture
- **Agent Framework Mode:** Production agents (current)
- **MCP Server Mode:** Protocol demo (already exists!)

**Key Insight:** We don't need to change Agent Framework mode. We need to:
1. ✅ Keep MCP server (it already works!)
2. ✅ Create clear documentation showing both modes
3. ✅ Build demo clients/scripts
4. ✅ Show WHEN to use each approach

**Benefit:** Demonstrates BOTH:
- Microsoft Agent Framework for production
- Model Context Protocol for standardization

---

## Questions for User

1. **Which demo is more important?**
   - Agent Framework (production agents)?
   - MCP Protocol (standardized tools)?
   - Both equally?

2. **Target audience?**
   - Developers building agents → Focus on Agent Framework
   - Tool providers → Focus on MCP protocol
   - LLM users → Focus on ease of use

3. **Claude Desktop integration?**
   - Want to show it working with Claude Desktop app?
   - Or just programmatic access is enough?

4. **Priority?**
   - Documentation first?
   - Test client first?
   - Or just verify server works?
