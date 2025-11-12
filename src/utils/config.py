import os
import yaml
from pathlib import Path
from typing import Any, Dict

# Try config.yaml first, fall back to default_config.yaml
CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
DEFAULT_CONFIG_PATH = CONFIG_DIR / "config.yaml"
if not DEFAULT_CONFIG_PATH.exists():
    DEFAULT_CONFIG_PATH = CONFIG_DIR / "default_config.yaml"


def load_config(path: str | None = None) -> Dict[str, Any]:
    """Load configuration from YAML and allow environment variable overrides.

    Args:
        path: Optional path to a YAML config file. If not provided, uses the
            repository's `config/default_config.yaml` if present.

    Returns:
        A dictionary with configuration values.
    """
    cfg_path = Path(path) if path else DEFAULT_CONFIG_PATH
    config: Dict[str, Any] = {}

    if cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as fh:
            config = yaml.safe_load(fh) or {}

    # Simple env overrides for top-level keys (dot-separated paths not supported)
    for key in list(config.keys()):
        env_key = key.upper()
        if env_key in os.environ:
            config[key] = os.environ[env_key]

    return config


def get(path: str, default: Any = None) -> Any:
    """Helper to get nested config values using dot-separated path.

    Example: get('processing.ocr_min_words')
    """
    parts = path.split(".") if path else []
    cfg = load_config()
    cur = cfg
    for p in parts:
        if isinstance(cur, dict) and p in cur:
            cur = cur[p]
        else:
            return default
    return cur


def get_mode() -> str:
    """Get the current operation mode (local, remote, or auto).

    Checks in order:
    1. Environment variable SCREENSHOT_ORGANIZER_MODE
    2. Config file demo.mode setting
    3. Default to "remote"

    Returns:
        Mode string: "local", "remote", or "auto"
    """
    # Check environment variable first
    env_mode = os.environ.get("SCREENSHOT_ORGANIZER_MODE")
    if env_mode and env_mode.lower() in ["local", "remote", "auto"]:
        return env_mode.lower()

    # Check config file
    config_mode = get("demo.mode", "remote")
    if config_mode and config_mode.lower() in ["local", "remote", "auto"]:
        return config_mode.lower()

    # Default
    return "remote"


def should_show_model_name() -> bool:
    """Check if model name should be displayed in responses."""
    return get("demo.show_model_name", True)


def should_show_latency() -> bool:
    """Check if latency should be displayed."""
    return get("demo.show_latency", False)


def should_show_cost() -> bool:
    """Check if cost estimates should be displayed."""
    return get("demo.show_cost_estimate", False)
