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

    # Suppress noisy third-party libraries for cleaner demo output
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("mcp.server.lowlevel.server").setLevel(logging.WARNING)
    logging.getLogger("mcp").setLevel(logging.WARNING)

    # Suppress MCP server startup messages (only show warnings/errors)
    logging.getLogger("__main__").setLevel(logging.WARNING)
    logging.getLogger("screenshot_mcp.server").setLevel(logging.WARNING)

    # Suppress CLI and agent client startup logs for cleaner demo
    logging.getLogger("cli_interface").setLevel(logging.WARNING)
    logging.getLogger("agent.client").setLevel(logging.WARNING)
    logging.getLogger("screenshot_mcp.client_wrapper").setLevel(logging.WARNING)

    # Suppress batch processor detailed logs
    logging.getLogger("organizers.batch_processor").setLevel(logging.WARNING)

    # Suppress all MCP tool operation logs (only show warnings/errors)
    for tool_name in [
        "screenshot_mcp.tools.list_screenshots",
        "screenshot_mcp.tools.analyze_screenshot",
        "screenshot_mcp.tools.move_screenshot",
        "screenshot_mcp.tools.create_category_folder",
        "screenshot_mcp.tools.categorize_screenshot",
        "screenshot_mcp.tools.generate_filename",
        "screenshot_mcp.tools.get_categories",
    ]:
        logging.getLogger(tool_name).setLevel(logging.WARNING)

    # Suppress vision processor detailed logs
    logging.getLogger("processors.azure_vision_processor").setLevel(logging.WARNING)

    # Suppress OCR processor logs
    logging.getLogger("processors.ocr_processor").setLevel(logging.WARNING)


def get_logger(name: str, level: Optional[str] = None) -> Logger:
    if level:
        logging.getLogger().setLevel(getattr(logging, level.upper(), logging.INFO))
    return logging.getLogger(name)
