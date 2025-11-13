# Quick Start - Mode Switching

## TL;DR

```bash
# Interactive mode selection at startup
python src/cli_interface.py

# Or force a specific mode with CLI flag
python src/cli_interface.py --local   # Local (Phi-4-mini, testing only)
python src/cli_interface.py           # Remote (Azure OpenAI, production)

# Compare both modes side-by-side
python scripts/demo_comparison.py
```

## Two Ways to Switch Modes

| Method | How | When to Use |
|--------|-----|-------------|
| **Interactive** | Just run `python src/cli_interface.py` | First time, exploring options |
| **CLI Flag** | Add `--mode local` or `--mode remote` | Automation, scripts, when you know what you want |

## Mode Comparison

| Feature | Local Mode | Remote Mode |
|---------|------------|-------------|
| **Command** | `--local` | (default) |
| **Purpose** | Testing conversation flow | Production demo |
| **Chat Model** | Phi-4-mini (AI Foundry) | GPT-4o (Azure OpenAI) |
| **Vision Model** | None (testing only) | GPT-4o Vision |
| **MCP Tools** | None (no file operations) | Full (7 tools) |
| **Cost** | $0 per query | ~$0.01-0.05 per query |
| **Setup** | `foundry service start` | Azure credentials |
| **Requirements** | AI Foundry CLI | Internet, API key |

## Setup

### Local Mode Setup
```bash
# Install AI Foundry CLI
brew install azure/ai-foundry/foundry

# Download Phi-4-mini
foundry model get phi-4-mini

# Start inference server
foundry service start

# Run screenshot organizer (testing mode only - no file operations)
python src/cli_interface.py --local
```

### Remote Mode Setup
```bash
export AZURE_AI_CHAT_ENDPOINT="https://xxx.openai.azure.com"
export AZURE_AI_MODEL_DEPLOYMENT="gpt-4o"
export AZURE_AI_CHAT_KEY="your-key"
python src/cli_interface.py
```

## Interactive Selection Example

When you run without `--mode`, you'll see:

```
╭────────────────────────╮
│ Screenshot Organizer   │
│ Select operation mode: │
╰────────────────────────╯

1. Local Mode (Testing Only)
   • Tests Agent Framework conversation flow
   • No file operations, no tools
   • Zero cost per query

2. Remote Mode (Production Demo)
   • Full MCP + Agent Framework demo
   • GPT-4o with 7 MCP tools
   • Requires: Azure credentials

Choose mode [1/2] (2): _
```

Press `1` or `2`, then Enter.

See [DEMO.md](DEMO.md) for full documentation.
