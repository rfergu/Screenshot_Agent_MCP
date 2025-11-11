import os
import yaml
from pathlib import Path
from typing import Any, Dict

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "default_config.yaml"


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
