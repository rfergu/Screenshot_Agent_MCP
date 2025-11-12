"""Create a category folder for organizing screenshots.

Creates the folder structure if it doesn't exist.
"""

from pathlib import Path
from typing import Annotated, Any, Dict, Optional

from pydantic import Field

from utils.logger import get_logger
from .shared import base_folder

logger = get_logger(__name__)


def create_category_folder(
    category: Annotated[str, Field(description="Category name (e.g., 'code', 'errors')")],
    base_dir: Annotated[Optional[str], Field(description="Base directory for organization (uses config default if not provided)")] = None
) -> Dict[str, Any]:
    """Create a category folder for organizing screenshots.

    Creates the folder structure if it doesn't exist.

    Args:
        category: Category name (e.g., "code", "errors")
        base_dir: Base directory for organization (optional)

    Returns:
        Dictionary containing:
        - folder_path: Absolute path to category folder
        - created: Whether the folder was newly created (False if it already existed)
        - success: Whether operation succeeded
    """
    # Normalize path by removing shell escape characters
    if base_dir:
        normalized_base = base_dir.replace('\\ ', ' ')  # Handle escaped spaces from shell
        base = Path(normalized_base).expanduser()
    else:
        base = Path(base_folder).expanduser()
    category_path = base / category

    logger.info(f"Creating category folder: {category_path}")

    created = False
    if not category_path.exists():
        category_path.mkdir(parents=True, exist_ok=True)
        created = True
        logger.info(f"Created new category folder: {category_path}")
    else:
        logger.debug(f"Category folder already exists: {category_path}")

    return {
        "folder_path": str(category_path),
        "created": created,
        "success": True
    }
