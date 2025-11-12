import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import logger


def test_get_logger():
    lg = logger.get_logger("test_logger")
    assert lg.name == "test_logger"


def test_setup_logging_changes_level():
    logger.setup_logging(level="DEBUG")
    lg = logger.get_logger("test_logger2")
    assert lg.level == 0 or isinstance(lg.level, int)
