"""List screenshot files in a directory.

Returns raw file information without any analysis or categorization.
The Agent decides what to do with the files.
"""

from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Dict, Optional

from pydantic import Field

from utils.logger import get_logger
from .shared import batch_processor

logger = get_logger(__name__)


def list_screenshots(
    directory: Annotated[str, Field(description="Absolute path to directory to scan for screenshots")],
    recursive: Annotated[bool, Field(description="Scan subdirectories recursively")] = False,
    max_files: Annotated[Optional[int], Field(description="Maximum number of files to return")] = None
) -> Dict[str, Any]:
    """List screenshot files in a directory.

    Returns raw file information without any analysis or categorization.
    The Agent decides what to do with the files.

    Args:
        directory: Absolute path to directory to scan
        recursive: Whether to scan subdirectories
        max_files: Maximum number of files to return (optional)

    Returns:
        Dictionary containing:
        - files: List of file information dicts
        - total_count: Total number of files found
        - truncated: Whether the list was truncated due to max_files limit
    """
    # Normalize path by removing shell escape characters
    normalized_dir = directory.replace('\\ ', ' ')  # Handle escaped spaces from shell
    dir_path = Path(normalized_dir).expanduser()
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {normalized_dir}")

    logger.info(f"Listing screenshots in {directory} (recursive={recursive})")

    # Scan for files
    files = batch_processor.scan_folder(dir_path, recursive=recursive)

    # Build file info list
    file_list = []
    for file_path in files:
        try:
            stat = file_path.stat()
            file_list.append({
                "path": str(file_path),
                "filename": file_path.name,
                "size_bytes": stat.st_size,
                "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        except Exception as e:
            logger.warning(f"Failed to stat file {file_path}: {e}")

    total_count = len(file_list)
    truncated = False

    # Apply max_files limit if specified
    if max_files and len(file_list) > max_files:
        file_list = file_list[:max_files]
        truncated = True
        logger.info(f"Truncated file list to {max_files} files (found {total_count})")

    return {
        "files": file_list,
        "total_count": total_count,
        "truncated": truncated
    }
