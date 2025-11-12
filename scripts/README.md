# Demo Scripts

This directory contains demonstration scripts showcasing the screenshot organizer's dual-mode capabilities.

## Available Demos

### demo_comparison.py - Side-by-Side Mode Comparison

Interactive demo that runs the same query through both LOCAL (Phi-3) and REMOTE (Azure OpenAI) modes, comparing:
- Response quality
- Latency
- Cost
- Privacy implications

**Usage:**
```bash
python scripts/demo_comparison.py
```

**Requirements:**
- For LOCAL mode: `pip install phi-3-vision-mlx`
- For REMOTE mode: Azure OpenAI credentials configured

**What it demonstrates:**
- Same Microsoft Agent Framework interface for both modes
- Same tool integration (analyze_screenshot, batch_process, organize_file)
- Trade-offs between local (privacy, zero cost) and remote (capability, latency)

## Mode Selection

The screenshot organizer supports three ways to select the operation mode:

### 1. CLI Flag (Highest Priority)
```bash
# Force local mode
python src/cli_interface.py --mode local

# Force remote mode
python src/cli_interface.py --mode remote
```

### 2. Environment Variable
```bash
# Set mode via environment
export SCREENSHOT_ORGANIZER_MODE=local
python src/cli_interface.py

# Or inline
SCREENSHOT_ORGANIZER_MODE=remote python src/cli_interface.py
```

### 3. Configuration File (Lowest Priority)
Edit `config/config.yaml`:
```yaml
demo:
  mode: "local"  # or "remote"
```

## Scenario Presets

The configuration file includes three demo scenarios optimized for different purposes:

### Privacy First (Fully Local)
```bash
# Edit config/config.yaml to use 'privacy_first' preset
demo:
  mode: "local"
  show_model_name: true
  show_cost_estimate: true  # Shows $0.00 for local
```

**Highlights:**
- Zero cost per query
- Complete privacy (no data leaves device)
- No API keys required
- ~8GB model loaded on first use

### Cloud Powered (Fully Remote)
```bash
# Edit config/config.yaml to use 'cloud_powered' preset
demo:
  mode: "remote"
  show_model_name: true
  show_latency: true
```

**Highlights:**
- Most capable models (GPT-4, GPT-4o, etc.)
- Faster cold-start (no model loading)
- Requires Azure credentials

### Comparison Mode (Auto-switch)
```bash
# Edit config/config.yaml to use 'comparison' preset
demo:
  mode: "auto"  # Not yet implemented - falls back to remote
  show_model_name: true
  show_latency: true
  show_cost_estimate: true
```

**Note:** Auto mode (local → remote fallback) is planned but not yet implemented.

## Local Mode Requirements

To use local mode, install the Phi-3 Vision MLX package:

```bash
pip install phi-3-vision-mlx
```

**System Requirements:**
- macOS with Apple Silicon (M1/M2/M3)
- ~8GB free RAM for model
- ~10GB disk space for model files

**First Use:**
- Model downloads automatically (~4GB)
- First query will be slow (model loading)
- Subsequent queries are much faster

## Remote Mode Requirements

Set these environment variables:

```bash
export AZURE_AI_CHAT_ENDPOINT="https://xxx.openai.azure.com"
export AZURE_AI_MODEL_DEPLOYMENT="gpt-4o"
export AZURE_AI_CHAT_KEY="your-api-key"
```

Or use Azure CLI authentication:
```bash
az login
# Then omit AZURE_AI_CHAT_KEY - uses DefaultAzureCredential
```

## Demo Tips

1. **Start with Remote Mode** - Faster cold-start, no model download
2. **Try Local Mode** - Shows privacy-first, zero-cost operation
3. **Compare Side-by-Side** - Use `demo_comparison.py` to see differences
4. **Show Cost Savings** - Enable `show_cost_estimate` in config
5. **Emphasize Privacy** - Local mode = zero data leaves device

## Architecture Highlights

Both modes use:
- **Same Microsoft Agent Framework interface**
- **Same tool integration** (embedded MCP tools)
- **Same conversation management** (AgentThread serialization)
- **Same CLI interface** (just different --mode flag)

The only difference:
- Local: `Phi3LocalChatClient` wraps phi-3-vision-mlx
- Remote: `AzureOpenAIChatClient` connects to Azure OpenAI

This demonstrates the flexibility of Microsoft Agent Framework for supporting multiple AI backends with zero code duplication.
