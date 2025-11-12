# Example Scripts

This directory contains example scripts for testing and demonstrating the screenshot organizer's capabilities.

## Available Examples

### demo_comparison.py - Side-by-Side Mode Comparison

Compares local (Phi-4-mini) vs remote (Azure OpenAI GPT-4o) modes side-by-side:
- Response quality
- Latency
- Cost implications
- Privacy trade-offs

**Usage:**
```bash
python scripts/demo_comparison.py
```

**Requirements:**
- **Local mode**: Azure AI Foundry CLI with Phi-4-mini running
- **Remote mode**: Azure OpenAI credentials configured

**What it demonstrates:**
- Same Microsoft Agent Framework interface for both modes
- Same conversational agent system (7-phase workflow)
- Trade-offs: local (privacy, testing) vs remote (production, full capabilities)

---

### Manual Testing Scripts

These scripts allow manual testing of specific components:

#### test_integration.py
Tests the complete MCP + Agent Framework integration:
- Agent Framework starts with MCP tools
- GPT-4 can call MCP tools via protocol
- File system access mediated through MCP

```bash
python scripts/test_integration.py
```

#### test_mcp_client.py
Tests MCP client wrapper functionality:
- MCP server subprocess launches correctly
- Tools are callable via MCP protocol
- Async tool execution works

```bash
python scripts/test_mcp_client.py
```

#### test_mcp_wrapper.py
Tests MCP wrapper integration:
- Tool registration with MCP server
- Tool call serialization/deserialization
- Error handling in tool calls

```bash
python scripts/test_mcp_wrapper.py
```

---

## Mode Selection

The screenshot organizer supports two operation modes:

### Remote Mode (Production - Default)
**Purpose:** Full AI agent capabilities with reliable tool support

**Setup:**
```bash
export AZURE_AI_CHAT_ENDPOINT="https://your-project.services.ai.azure.com/api/projects/your-project"
export AZURE_AI_MODEL_DEPLOYMENT="gpt-4o"
export AZURE_AI_CHAT_KEY="your_api_key"
```

**Features:**
- ✅ Azure OpenAI GPT-4o with complete tool calling
- ✅ Full MCP tool support (5 file operation tools)
- ✅ Screenshot analysis (OCR + Azure GPT-4o Vision)
- ✅ Complete file organization capabilities
- ✅ Proactive conversational UX (7-phase workflow)

**CLI:**
```bash
# Remote mode is default
python -m src.cli_interface

# Or programmatically:
from agent_client import AgentClient
client = AgentClient(mode="remote")
```

### Local Mode (Testing/Debugging Only)
**Purpose:** Quick testing of conversation flow without API costs

**Setup:**
```bash
# Install Azure AI Foundry CLI (macOS)
brew install azure/ai-foundry/foundry

# Download and start Phi-4-mini
foundry model get phi-4-mini
foundry service start
foundry model load phi-4-mini

# Verify it's running
foundry service status
```

**Features:**
- ✅ Basic chat for testing agent instructions
- ✅ Fast iteration without API costs
- ❌ NO tool support (testing conversation flow only)
- ❌ NO screenshot analysis
- ❌ NO file organization

**CLI:**
```bash
# Use --local flag
python -m src.cli_interface --local

# Or programmatically:
from agent_client import AgentClient
client = AgentClient(mode="local")
```

**Use Cases:**
- Testing system prompts
- Validating agent instructions
- Fast iteration on conversational UX
- Debugging conversation flow

---

## Architecture Highlights

Both modes use the **same Microsoft Agent Framework interface:**

- **Same conversation management** (AgentThread serialization)
- **Same system prompts** (7-phase conversational workflow)
- **Same CLI interface** (just different `--local` flag)

**The only difference:**
- **Local**: `LocalFoundryChatClient` connects to Foundry inference server (Phi-4-mini)
- **Remote**: `AzureOpenAIChatClient` connects to Azure OpenAI (GPT-4o)

In remote mode, **Agent Framework WITH MCP Client Integration** is active:
```
Agent Framework (Brain 🧠)
    ↓ contains
MCP Client Wrapper (EMBEDDED)
    ↓ calls via stdio
MCP Server (Hands 🤲)
    ↓ operates on
File System
```

This demonstrates:
- **Agent Framework capabilities**: Intelligent orchestration, tool calling
- **MCP protocol integration**: Standardized tool interface
- **Dual-mode flexibility**: Same framework, different backends

---

## Demo Tips

1. **Start with Remote Mode** - Shows full production capabilities
2. **Try Local Mode** - Shows testing/debugging workflow
3. **Compare Side-by-Side** - Use `demo_comparison.py` to see differences
4. **Emphasize Architecture** - Show MCP protocol in action (remote mode)
5. **Show Proactive UX** - Agent introduces itself and guides user through 7 phases

---

## Notes

- For production work, **always use remote mode** (reliable tool calling)
- Local mode is **testing only** (no file operations, no screenshot analysis)
- All manual test scripts require remote mode (MCP tools active)
- See main [README.md](../README.md) for complete installation instructions
