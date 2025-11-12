# Screenshot Organizer Demo Guide

## Switching Between Local and Remote Modes

The screenshot organizer supports **two ways** to select the operation mode:

### Method 1: Interactive Selection at Startup (Default)

Simply run the program without any flags:

```bash
python src/cli_interface.py
```

You'll see an interactive prompt:

```
╭────────────────────────╮
│ Screenshot Organizer   │
│                        │
│ Select operation mode: │
╰────────────────────────╯

1. Local Mode (Phi-3 Vision MLX)
   • Fully on-device, complete privacy
   • Zero cost per query
   • Requires: phi-3-vision-mlx package

2. Remote Mode (Azure OpenAI)
   • Cloud-powered, more capable
   • Requires: Azure credentials
   • ~$0.01-0.05 per query

Choose mode [1/2] (2): _
```

- Press `1` for Local Mode
- Press `2` for Remote Mode (default)
- Press Enter to accept the default (Remote)

### Method 2: CLI Flag (Skip Interactive Prompt)

Force a specific mode using the `--mode` flag:

```bash
# Use local mode (Phi-3 Vision MLX on-device)
python src/cli_interface.py --mode local

# Use remote mode (Azure OpenAI cloud)
python src/cli_interface.py --mode remote
```

When using `--mode`, the interactive prompt is **skipped** and the specified mode is used directly.

## Quick Start Examples

### Remote Mode (Default)

**Requirements:**
- Azure OpenAI credentials configured
- Environment variables set (see below)

**Usage:**
```bash
python src/cli_interface.py
```

**Setup:**
```bash
export AZURE_AI_CHAT_ENDPOINT="https://xxx.openai.azure.com"
export AZURE_AI_MODEL_DEPLOYMENT="gpt-4o"
export AZURE_AI_CHAT_KEY="your-api-key"
```

### Local Mode

**Requirements:**
- `pip install phi-3-vision-mlx`
- macOS with Apple Silicon (M1/M2/M3)
- ~8GB free RAM

**Usage:**
```bash
python src/cli_interface.py --mode local
```

**First Run:**
- Model will download automatically (~4GB)
- First query will be slow (model loading)
- Subsequent queries are faster

## Mode Indicators

When you start the CLI, you'll see which mode is active:

```
╭────────────────────────────────────────────────╮
│ Screenshot Organizer AI Assistant              │
│                                                 │
│ 🏠 LOCAL MODE - phi-3-vision-mlx               │
│ • Running fully on-device with Phi-3 Vision    │
│ • Zero cost, complete privacy                  │
╰────────────────────────────────────────────────╯
```

or

```
╭────────────────────────────────────────────────╮
│ Screenshot Organizer AI Assistant              │
│                                                 │
│ ☁️  REMOTE MODE - gpt-4o                       │
│ • Running on Azure OpenAI cloud                │
│ • More capable models, requires API access     │
╰────────────────────────────────────────────────╯
```

If `show_model_name: true` in config, each response shows:

```
Assistant 🏠 local
I support the following categories...
```

or

```
Assistant ☁️ remote
I support the following categories...
```

## Demo Comparison Utility

Run both modes side-by-side:

```bash
python scripts/demo_comparison.py
```

This will:
1. Ask you to select a demo query
2. Run the same query through both local and remote
3. Display responses, latency, and cost differences

**Requirements:**
- Both modes must be configured
- Local: phi-3-vision-mlx installed
- Remote: Azure credentials set

## Configuration Options

Edit `config/config.yaml` to customize:

```yaml
demo:
  mode: "remote"              # Default mode
  show_model_name: true       # Show mode indicator in responses
  show_latency: false         # Show response timing
  show_cost_estimate: false   # Show estimated costs
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

Or switch to local mode: `--mode local`

### "phi-3-vision-mlx not available"

**Issue:** Local mode requires phi-3-vision-mlx package

**Solution:**
```bash
pip install phi-3-vision-mlx
```

Or switch to remote mode: `--mode remote`

### Want to see which mode will be used?

```bash
python -c "
import sys
sys.path.insert(0, 'src')
from utils.config import get_mode
print(f'Current mode: {get_mode()}')
"
```

## What's the Same in Both Modes?

Regardless of mode, you get:
- ✓ Same three tools (analyze_screenshot, batch_process, organize_file)
- ✓ Same Microsoft Agent Framework orchestration
- ✓ Same conversation interface
- ✓ Same session persistence
- ✓ Same CLI commands

The **only difference** is which AI model handles the conversation:
- **Local:** Phi-3 Vision MLX (on your device)
- **Remote:** Azure OpenAI GPT-4 (in the cloud)
