import os
from src.utils import config


def test_load_config_defaults():
    cfg = config.load_config()
    assert isinstance(cfg, dict)
    # expected top-level keys
    assert "processing" in cfg
    assert "organization" in cfg


def test_get_helper():
    # should return default when path not present
    assert config.get("non.existing.path", default=123) == 123
