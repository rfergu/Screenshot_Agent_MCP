"""Analyze screenshot content using OCR or vision model.

Returns RAW analysis data (extracted text, descriptions).
Does NOT make categorization or filename decisions - that's the Agent's job.
"""

import time
from pathlib import Path
from typing import Annotated, Any, Dict

from pydantic import Field

from utils.logger import get_logger
from .shared import ocr_processor, vision_processor

logger = get_logger(__name__)


def analyze_screenshot(
    file_path: Annotated[str, Field(description="Absolute path to screenshot file to analyze")],
    force_vision: Annotated[bool, Field(description="Skip OCR and use vision model directly")] = False
) -> Dict[str, Any]:
    """Analyze screenshot content using OCR or vision model.

    Returns RAW analysis data (extracted text, descriptions).
    Does NOT make categorization or filename decisions - that's the Agent's job.

    Args:
        file_path: Absolute path to screenshot file
        force_vision: If True, skip OCR and use vision model directly

    Returns:
        Dictionary containing:
        - extracted_text: Text extracted via OCR (if applicable)
        - vision_description: Description from vision model (if applicable)
        - processing_method: "ocr" or "vision"
        - processing_time_ms: Time taken to process
        - word_count: Number of words extracted (if OCR)
        - success: Whether analysis succeeded
        - error: Error message if failed (None if successful)
    """
    # Normalize path by handling shell escapes
    normalized_path = file_path.replace('\\ ', ' ')  # Handle escaped spaces from shell
    path_obj = Path(normalized_path).expanduser()

    # macOS uses Unicode narrow no-break space (U+202F) before AM/PM in screenshot filenames
    # Try both variations: with regular spaces and with U+202F before AM/PM
    if not path_obj.exists():
        dir_path = path_obj.parent
        filename = path_obj.name

        # Try replacing space before AM/PM with U+202F (macOS default)
        import re
        unicode_filename = re.sub(r' (AM|PM)', '\u202f\\1', filename)
        unicode_path_obj = dir_path / unicode_filename
        if unicode_path_obj.exists():
            path_obj = unicode_path_obj
        else:
            # Also try the reverse: U+202F before AM/PM -> regular space
            regular_filename = re.sub('\u202f(AM|PM)', r' \1', filename)
            regular_path_obj = dir_path / regular_filename
            if regular_path_obj.exists():
                path_obj = regular_path_obj

    if not path_obj.exists():
        raise FileNotFoundError(f"Screenshot file not found: {normalized_path}")

    logger.debug(f"Analyzing screenshot: {file_path} (force_vision={force_vision})")
    start_time = time.perf_counter()

    response = {
        "extracted_text": None,
        "vision_description": None,
        "processing_method": "unknown",
        "processing_time_ms": 0.0,
        "word_count": 0,
        "success": False,
        "error": None
    }

    try:
        if force_vision:
            # Use vision model
            logger.debug("force_vision=True, using vision model")
            vision_result = vision_processor.process(path_obj)
            response.update({
                "vision_description": vision_result.description,
                "processing_method": "vision",
                "success": True
            })
        else:
            # Try OCR first
            logger.debug("Attempting OCR extraction")
            try:
                ocr_result = ocr_processor.process(path_obj)
                response.update({
                    "extracted_text": ocr_result.text,
                    "word_count": ocr_result.word_count,
                    "processing_method": "ocr",
                    "success": True
                })

                # If insufficient text, add vision description
                if not ocr_result.sufficient_text:
                    logger.debug("Insufficient OCR text, adding vision analysis")
                    vision_result = vision_processor.process(path_obj)
                    response["vision_description"] = vision_result.description
                    response["processing_method"] = "vision"

            except Exception as ocr_error:
                # OCR failed, fall back to vision processing
                logger.warning(f"OCR failed ({ocr_error}), falling back to vision model")
                vision_result = vision_processor.process(path_obj)
                response.update({
                    "vision_description": vision_result.description,
                    "processing_method": "vision",
                    "success": True
                })

        response["processing_time_ms"] = (time.perf_counter() - start_time) * 1000

        logger.debug(
            f"Analysis complete: {path_obj.name} via {response['processing_method']} "
            f"in {response['processing_time_ms']:.2f}ms"
        )

        return response

    except Exception as e:
        response["success"] = False
        response["error"] = str(e)
        response["processing_time_ms"] = (time.perf_counter() - start_time) * 1000
        logger.error(f"Failed to analyze screenshot {file_path}: {e}")
        raise
