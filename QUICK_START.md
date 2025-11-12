# Quick Start - Mode Switching

## TL;DR

```bash
# Interactive mode selection at startup
python src/cli_interface.py

# Or force a specific mode with CLI flag
python src/cli_interface.py --mode local   # Local (Phi-3)
python src/cli_interface.py --mode remote  # Remote (Azure OpenAI)

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
| **Command** | `--mode local` | `--mode remote` (default) |
| **Model** | Phi-3 Vision MLX | Azure OpenAI (GPT-4) |
| **Cost** | $0 per query | ~$0.01-0.05 per query |
| **Privacy** | Complete (on-device) | Cloud processed |
| **Setup** | `pip install phi-3-vision-mlx` | Azure credentials |
| **First Run** | Slow (model download) | Fast |
| **Requirements** | M1/M2/M3 Mac, ~8GB RAM | Internet, API key |

## Setup

### Local Mode Setup
```bash
pip install phi-3-vision-mlx
python src/cli_interface.py --mode local
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

1. Local Mode (Phi-3 Vision MLX)
   • Fully on-device, complete privacy
   • Zero cost per query

2. Remote Mode (Azure OpenAI)
   • Cloud-powered, more capable
   • Requires: Azure credentials

Choose mode [1/2] (2): _
```

Press `1` or `2`, then Enter.

See [DEMO.md](DEMO.md) for full documentation.
