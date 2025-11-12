"""Generate a descriptive filename for a screenshot.

This is a simple utility for generating filenames. The Agent (GPT-4)
can use its own intelligence to generate better filenames if desired.
"""

from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Dict, Optional

from pydantic import Field

from utils.logger import get_logger

logger = get_logger(__name__)


def generate_filename(
    original_filename: Annotated[str, Field(description="Original filename")],
    category: Annotated[str, Field(description="Category name")],
    text: Annotated[Optional[str], Field(description="Optional extracted text for generating descriptive name")] = None,
    description: Annotated[Optional[str], Field(description="Optional description for generating descriptive name")] = None
) -> Dict[str, Any]:
    """Generate a descriptive filename for a screenshot.

    This is a simple utility for generating filenames. The Agent (GPT-4)
    can use its own intelligence to generate better filenames if desired.

    Args:
        original_filename: Original file name
        category: Category name
        text: Optional extracted text (first few words used)
        description: Optional description from vision model

    Returns:
        Dictionary containing:
        - suggested_filename: Generated filename (without extension)
        - extension: File extension
        - timestamp: Timestamp string
    """
    logger.debug(f"Generating filename for {original_filename} (category={category})")

    # Get extension from original
    extension = Path(original_filename).suffix

    # Generate timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d")

    # Try to generate descriptive name from text or description
    if text:
        # Take first meaningful words (up to 5)
        words = [w for w in text.split() if len(w) > 2][:5]
        if words:
            base_name = "_".join(words).lower()
            suggested = f"{base_name}_{timestamp}"
            return {
                "suggested_filename": suggested,
                "extension": extension,
                "timestamp": timestamp
            }

    if description:
        # Take first few words from description
        words = [w for w in description.split() if len(w) > 2][:5]
        if words:
            base_name = "_".join(words).lower()
            suggested = f"{base_name}_{timestamp}"
            return {
                "suggested_filename": suggested,
                "extension": extension,
                "timestamp": timestamp
            }

    # Fallback: category + timestamp
    suggested = f"{category}_screenshot_{timestamp}"
    return {
        "suggested_filename": suggested,
        "extension": extension,
        "timestamp": timestamp
    }
