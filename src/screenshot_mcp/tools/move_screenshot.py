"""Move (or copy) a screenshot file to a destination folder.

Simple file operation - just moves/copies the file as instructed.
The Agent decides the destination and new filename.
"""

from pathlib import Path
from typing import Annotated, Any, Dict, Optional

from pydantic import Field

from utils.logger import get_logger

logger = get_logger(__name__)


def move_screenshot(
    source_path: Annotated[str, Field(description="Absolute path to source file")],
    dest_folder: Annotated[str, Field(description="Absolute path to destination folder")],
    new_filename: Annotated[Optional[str], Field(description="New filename (without extension). If None, keeps original name")] = None,
    keep_original: Annotated[bool, Field(description="If True, copy instead of move")] = True
) -> Dict[str, Any]:
    """Move (or copy) a screenshot file to a destination folder.

    Simple file operation - just moves/copies the file as instructed.
    The Agent decides the destination and new filename.

    Args:
        source_path: Absolute path to source file
        dest_folder: Absolute path to destination folder
        new_filename: Optional new filename (without extension)
        keep_original: If True, copy instead of move

    Returns:
        Dictionary containing:
        - original_path: Original file path
        - new_path: New file path after move/copy
        - operation: "copy" or "move"
        - success: Whether operation succeeded
        - error: Error message if failed (None if successful)
    """
    # Normalize paths by handling shell escapes
    normalized_source = source_path.replace('\\ ', ' ')  # Handle escaped spaces from shell
    normalized_dest = dest_folder.replace('\\ ', ' ')  # Handle escaped spaces from shell

    source = Path(normalized_source).expanduser()

    # macOS uses Unicode narrow no-break space (U+202F) before AM/PM in screenshot filenames
    # Try both variations: with regular spaces and with U+202F before AM/PM
    if not source.exists():
        import re
        dir_path = source.parent
        filename = source.name

        # Try replacing space before AM/PM with U+202F (macOS default)
        unicode_filename = re.sub(r' (AM|PM)', '\u202f\\1', filename)
        unicode_path_obj = dir_path / unicode_filename
        if unicode_path_obj.exists():
            source = unicode_path_obj
        else:
            # Also try the reverse: U+202F before AM/PM -> regular space
            regular_filename = re.sub('\u202f(AM|PM)', r' \1', filename)
            regular_path_obj = dir_path / regular_filename
            if regular_path_obj.exists():
                source = regular_path_obj

    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {normalized_source}")

    dest_dir = Path(normalized_dest).expanduser()
    if not dest_dir.exists():
        raise FileNotFoundError(f"Destination folder not found: {normalized_dest}")

    # Determine destination filename
    if new_filename:
        # Use new filename but keep original extension
        extension = source.suffix
        dest_path = dest_dir / f"{new_filename}{extension}"
    else:
        # Keep original filename
        dest_path = dest_dir / source.name

    logger.info(
        f"{'Copying' if keep_original else 'Moving'} screenshot: "
        f"{source.name} → {dest_path}"
    )

    try:
        operation = ""
        if keep_original:
            import shutil
            shutil.copy2(source, dest_path)
            operation = "copy"
        else:
            source.rename(dest_path)
            operation = "move"

        logger.info(f"Successfully {operation}ed {source.name} to {dest_path}")

        return {
            "original_path": str(source),
            "new_path": str(dest_path),
            "operation": operation,
            "success": True,
            "error": None
        }

    except Exception as e:
        logger.error(f"Failed to {operation} {source.name}: {e}")
        return {
            "original_path": str(source),
            "new_path": None,
            "operation": operation,
            "success": False,
            "error": str(e)
        }
