# Screenshot Organizer Demo Guide

## Modes Overview

The screenshot organizer demonstrates **production AI agent development** with two distinct modes:

### Remote Mode (PRODUCTION - Recommended)
- **Purpose:** Full AI agent capabilities for actual screenshot organization
- **Model:** Azure OpenAI GPT-4o
- **Tools:** All three tools available (analyze_screenshot, batch_process, organize_file)
- **Use Cases:** Production screenshot organization, batch processing, reliable categorization

### Local Mode (TESTING ONLY)
- **Purpose:** Quick testing of agent conversation flow and instructions
- **Model:** Azure AI Foundry Phi-4-mini (local inference server)
- **Tools:** NONE - basic chat responses only
- **Use Cases:** Testing system prompts, validating agent instructions, fast iteration without API costs

## Switching Between Modes

### Method 1: Interactive Selection at Startup (Default)

Simply run the program without any flags:

```bash
python -m src.cli_interface
```

You'll see an interactive prompt:

```
╭────────────────────────╮
│ Screenshot Organizer   │
│                        │
│ Select operation mode: │
╰────────────────────────╯

1. Local Mode (TESTING ONLY)
   • Basic chat for testing conversation flow
   • NO tools (no screenshot analysis)
   • Requires: Azure AI Foundry CLI running

2. Remote Mode (PRODUCTION - RECOMMENDED)
   • Full AI agent capabilities with tool support
   • Screenshot analysis, file organization
   • Requires: Azure credentials

Choose mode [1/2] (2): _
```

- Press `1` for Local Mode (testing)
- Press `2` for Remote Mode (production, default)
- Press Enter to accept the default (Remote)

### Method 2: CLI Flag (Skip Interactive Prompt)

Force a specific mode using the `--mode` flag:

```bash
# Use local mode (testing only, no tools)
python -m src.cli_interface --mode local

# Use remote mode (production with full tools)
python -m src.cli_interface --mode remote
```

## Quick Start Examples

### Remote Mode (Production - Recommended)

**Requirements:**
- Azure OpenAI credentials configured
- Environment variables set

**Setup:**
```bash
export AZURE_AI_CHAT_ENDPOINT="https://your-endpoint.cognitiveservices.azure.com"
export AZURE_AI_MODEL_DEPLOYMENT="gpt-4o"
export AZURE_AI_CHAT_KEY="your-api-key"
```

**Usage:**
```bash
python -m src.cli_interface --mode remote
```

**What You Can Do:**
- Analyze individual screenshots
- Batch process entire folders
- Organize and rename files automatically
- Get intelligent categorization suggestions

**Example Session:**
```
You: Analyze this screenshot: ~/Desktop/screenshot.png
Assistant: I'll analyze that screenshot...
[Full analysis with category, filename suggestion, processing method]

You: Organize all screenshots in ~/Desktop/screenshots
Assistant: I found 15 screenshots. Should I organize them?
You: Yes
Assistant: Done! Organized 15 screenshots into categories...
```

### Local Mode (Testing Only)

**Requirements:**
- Azure AI Foundry CLI installed: `brew install azure/ai-foundry/foundry`
- Phi-4-mini downloaded: `foundry model get phi-4-mini`

**Setup:**
```bash
# 1. Start AI Foundry inference server
foundry service start
foundry model load phi-4-mini

# 2. Run the screenshot organizer in local mode
python -m src.cli_interface --mode local
```

**What You Can Do:**
- Test agent conversation flow
- Validate system prompt behavior
- Check instruction following
- Quick testing without API costs

**What You CANNOT Do:**
- ✗ Analyze screenshots
- ✗ Organize files
- ✗ Batch processing
- ✗ Any tool-based operations

**Example Session:**
```
You: What can you help me with?
Assistant: In Local Testing Mode, I'm here to assist you with testing
conversation flows, following instructions, and providing responses of
good quality and tone. While I can't provide screenshots or help with
file organization, I can help test the conversational aspects of the agent.

For production use with screenshot analysis and file organization, please
switch to remote mode (GPT-4).
```

## Mode Indicators

When you start the CLI, you'll see which mode is active:

**Local Mode:**
```
╭────────────────────────────────────────────────╮
│ Screenshot Organizer AI Assistant              │
│                                                 │
│ 🏠 LOCAL MODE - phi-4-mini (local)            │
│ • TESTING MODE: Basic chat only (no tools)     │
│ • Use for quick testing of conversation flow   │
│ • Switch to remote mode for production use     │
╰────────────────────────────────────────────────╯
```

**Remote Mode:**
```
╭────────────────────────────────────────────────╮
│ Screenshot Organizer AI Assistant              │
│                                                 │
│ ☁️  REMOTE MODE - gpt-4o                       │
│ • PRODUCTION MODE: Full AI agent capabilities  │
│ • Screenshot analysis, file organization       │
│ • Running on Azure OpenAI cloud infrastructure │
╰────────────────────────────────────────────────╯
```

If `show_model_name: true` in config, each response shows:

**Local:**
```
Assistant 🏠 local
I'm here to test conversation flows...
```

**Remote:**
```
Assistant ☁️ remote
I'll analyze that screenshot for you...
```

## Configuration Options

Edit `config/config.yaml` to customize:

```yaml
demo:
  mode: "remote"              # Default mode (remote = production)
  show_model_name: true       # Show mode indicator in responses
  show_latency: false         # Show response timing
  show_cost_estimate: false   # Show estimated costs

local:
  # TESTING ONLY mode configuration
  endpoint: "auto"            # Auto-detect Foundry endpoint
  model: "phi-4-mini"
  # See config comments for full details

remote:
  # PRODUCTION mode configuration
  provider: "azure_openai"
  # Uses environment variables for credentials
```

## Troubleshooting

### "Azure credentials not configured"

**Issue:** Remote mode requires Azure credentials

**Solution:**
```bash
export AZURE_AI_CHAT_ENDPOINT="your-endpoint"
export AZURE_AI_CHAT_KEY="your-key"
export AZURE_AI_MODEL_DEPLOYMENT="gpt-4o"
```

Or switch to local mode for testing: `--mode local`

### "Foundry service not running"

**Issue:** Local mode requires AI Foundry inference server

**Solution:**
```bash
foundry service status  # Check status
foundry service start   # Start if stopped
foundry model load phi-4-mini  # Load model
```

Or switch to remote mode: `--mode remote`

### "Local mode doesn't have tools"

**This is by design!** Local mode is for testing conversation flow only.

**Reason:** Small local models (Phi-4-mini) are unreliable for tool calling:
- Ignore tools
- Hallucinate function calls
- Generate garbled JSON

**Solution:** Use remote mode for actual screenshot organization work.

## Architecture Reality

This project demonstrates the **reality of production AI agent development**:

### Small Local Models (Phi-4-mini)
- ✓ Good: Basic chat, conversation flow testing
- ✗ Unreliable: Function calling, tool integration
- **Use Case:** Quick testing without API costs

### Large Remote Models (GPT-4)
- ✓ Good: Everything - chat, tools, vision, reasoning
- ✓ Reliable: Robust function calling and tool orchestration
- **Use Case:** Production applications

## What's the Same in Both Modes?

Both modes use:
- ✓ Same Microsoft Agent Framework
- ✓ Same AgentClient wrapper
- ✓ Same conversation interface
- ✓ Same CLI commands
- ✓ Same session persistence

The **difference** is capability:
- **Local:** Basic chat only (testing)
- **Remote:** Full tools + chat (production)

## Architecture: Agent Framework WITH MCP Client

This demo showcases **Microsoft Agent Framework WITH MCP Client Integration** - a modern approach to AI agent development.

### Unified Architecture (Remote Mode)

```
User Request: "organize my screenshots"
    ↓
Agent Framework (Brain 🧠)
    • GPT-4 understands intent
    • Makes intelligent decisions (categories, filenames)
    • Orchestrates workflow
    ↓ contains
MCP Client Wrapper (EMBEDDED)
    • Manages MCP server subprocess
    • Provides tool interface
    • Handles protocol communication
    ↓ calls via stdio
MCP Server (Hands 🤲)
    • Provides low-level file operation tools
    • Just executes what Agent tells it
    • Returns facts, not decisions
    ↓
File System (ALL access through MCP!)
```

**Key Principle:** The Agent Framework contains an embedded MCP client that connects to an MCP server for ALL file operations. This demonstrates the Model Context Protocol (MCP) standard for tool integration.

### Remote Mode Components

1. **Agent Framework (Orchestrator)**
   - Uses GPT-4 for intelligent decision-making
   - Decides categorization and naming
   - Orchestrates tool calls

2. **MCP Client (Embedded Bridge)**
   - Embedded inside Agent Framework
   - Manages MCP server subprocess
   - Provides tool wrappers

3. **MCP Server (Tool Provider)**
   - Runs as separate subprocess
   - Exposes 7 low-level file operation tools
   - Mediates all file system access

### Local Mode (Testing Only)

Local mode intentionally does NOT use tools:
- **Why:** Small models (Phi-4-mini) are unreliable for function calling
- **Purpose:** Test conversation flow and system prompts only
- **No MCP:** MCP integration only active in remote mode

## Why This Architecture?

1. **Demonstrates MCP Protocol:** Shows standardized tool integration for LLMs
2. **Shows Production Reality:** Demonstrates that small models aren't production-ready for tool-based agents
3. **Separation of Concerns:** Brain (Agent) vs Hands (MCP) - clear architectural boundaries
4. **Honest Communication:** Clear about what each mode can and cannot do
5. **Best Tool for the Job:** Use small models for testing, large models for production
6. **Educational Value:** Teaches developers about AI model tradeoffs and modern agent architecture

## Recommendations

- **For Testing:** Use local mode to iterate on system prompts and conversation flow
- **For Production:** Always use remote mode for actual screenshot organization
- **For Privacy:** Remote mode can use Azure GPT-4o Vision as fallback (images stay local)
- **Default:** Remote mode is the default for good reason - it actually works!
