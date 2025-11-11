import logging
from logging import Logger
from typing import Optional


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    handlers = [logging.StreamHandler()]
    if log_file:
        handlers.append(logging.FileHandler(log_file))

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=handlers,
    )


def get_logger(name: str, level: Optional[str] = None) -> Logger:
    if level:
        logging.getLogger().setLevel(getattr(logging, level.upper(), logging.INFO))
    return logging.getLogger(name)
