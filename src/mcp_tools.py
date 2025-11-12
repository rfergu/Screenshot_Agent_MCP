"""Tool functions for screenshot analysis and organization.

These functions are designed to be used directly with Microsoft Agent Framework.
Each function uses type annotations and Pydantic Field descriptions for automatic
tool discovery and schema generation.
"""

import time
from pathlib import Path
from typing import Annotated, Any, Dict, Optional

from pydantic import Field

from classifiers.keyword_classifier import KeywordClassifier
from organizers.batch_processor import BatchProcessor
from organizers.file_organizer import FileOrganizer
from processors.ocr_processor import OCRProcessor
from processors.vision_processor import VisionProcessor
from utils.config import get as config_get
from utils.logger import get_logger

logger = get_logger(__name__)

# Initialize processors and organizers at module level
# These are shared across all tool function calls
_ocr_min_words = config_get("processing.ocr_min_words", 10)
_ocr_processor = OCRProcessor(min_words_threshold=_ocr_min_words)
_vision_processor = VisionProcessor()
_classifier = KeywordClassifier()

_base_folder = config_get("organization.base_folder", "~/Screenshots/organized")
_categories = config_get("organization.categories", ["code", "errors", "documentation", "design", "communication", "memes", "other"])
_keep_originals = config_get("organization.keep_originals", True)
_file_organizer = FileOrganizer(_base_folder, _categories, _keep_originals)

_batch_processor = BatchProcessor()

logger.info("Screenshot tools initialized with all processors and organizers")


def analyze_screenshot(
    path: Annotated[str, Field(description="Absolute path to the screenshot file")],
    force_vision: Annotated[bool, Field(description="Force use of vision model even if OCR would be sufficient")] = False
) -> Dict[str, Any]:
    """Analyze a screenshot using tiered OCR → keyword → vision approach.

    The tool intelligently processes screenshots by:
    1. First attempting OCR text extraction (fast, ~50ms)
    2. If sufficient text found (>10 words), uses keyword-based classification
    3. If insufficient text, falls back to vision model analysis (~2s)
    4. Returns category, suggested filename, and processing details

    Args:
        path: Absolute path to the screenshot file
        force_vision: If True, skip OCR and use vision model directly

    Returns:
        Dictionary containing:
        - category: One of (code, errors, documentation, design, communication, memes, other)
        - suggested_filename: Descriptive filename based on content
        - description: Brief description of screenshot content
        - processing_method: "ocr" or "vision"
        - processing_time_ms: Time taken to process
        - confidence_score: Confidence in classification (0.0-1.0)
        - extracted_text: Text extracted via OCR (if applicable)
    """
    path_obj = Path(path)
    if not path_obj.exists():
        raise FileNotFoundError(f"Screenshot file not found: {path}")

    logger.info(f"Analyzing screenshot: {path} (force_vision={force_vision})")
    start_time = time.perf_counter()

    # Initialize response
    response: Dict[str, Any] = {
        "category": "other",
        "suggested_filename": path_obj.stem,
        "description": "",
        "processing_method": "unknown",
        "processing_time_ms": 0.0,
        "confidence_score": 0.0,
        "extracted_text": None
    }

    try:
        if force_vision:
            # Skip OCR, go straight to vision
            logger.debug("force_vision=True, using vision model")
            response.update(_process_with_vision(path_obj))
        else:
            # Tiered approach: OCR → keyword classification → vision if needed
            logger.debug("Starting tiered approach: OCR first")
            ocr_result = _ocr_processor.process(path_obj)
            response["extracted_text"] = ocr_result.text

            if ocr_result.sufficient_text:
                # OCR extracted enough text, classify it
                logger.debug(f"Sufficient text found ({ocr_result.word_count} words), classifying")
                category = _classifier.classify(ocr_result.text)

                response.update({
                    "category": category,
                    "suggested_filename": _generate_filename_from_text(ocr_result.text, category),
                    "description": _generate_description_from_text(ocr_result.text),
                    "processing_method": "ocr",
                    "confidence_score": 0.8  # High confidence for text-based classification
                })
            else:
                # Insufficient text, fall back to vision
                logger.debug(f"Insufficient text ({ocr_result.word_count} words), falling back to vision")
                response.update(_process_with_vision(path_obj))

        # Calculate total processing time
        response["processing_time_ms"] = (time.perf_counter() - start_time) * 1000

        logger.info(
            f"Analysis complete: {path_obj.name} → {response['category']} "
            f"({response['processing_method']}) in {response['processing_time_ms']:.2f}ms"
        )

        return response

    except Exception as e:
        logger.error(f"Failed to analyze screenshot {path}: {e}")
        raise


def batch_process(
    folder: Annotated[str, Field(description="Path to the folder containing screenshots")],
    recursive: Annotated[bool, Field(description="Process subfolders recursively")] = False,
    max_files: Annotated[Optional[int], Field(description="Maximum number of files to process (1-1000)")] = None,
    organize: Annotated[bool, Field(description="Automatically organize files after analysis")] = False
) -> Dict[str, Any]:
    """Process all screenshots in a folder with batch analysis and organization.

    Scans a folder for image files and processes each one using the same tiered
    approach as analyze_screenshot. Provides detailed statistics on processing
    methods used, categories found, and timing information.

    Args:
        folder: Path to the folder containing screenshots
        recursive: If True, process subfolders recursively
        max_files: Maximum number of files to process (1-1000)
        organize: If True, automatically organize files after analysis

    Returns:
        Dictionary containing:
        - total_files: Number of files found
        - successful: Number of files successfully processed
        - failed: Number of files that failed processing
        - ocr_processed: Number of files processed via OCR
        - vision_processed: Number of files processed via vision model
        - total_time_ms: Total processing time
        - average_time_per_file_ms: Average time per file
        - categories_count: Dictionary of category counts
        - processed_files: List of processed file details
        - errors: List of error details for failed files
    """
    folder_path = Path(folder)
    if not folder_path.exists():
        raise FileNotFoundError(f"Folder not found: {folder}")

    logger.info(
        f"Starting batch processing: folder={folder}, recursive={recursive}, "
        f"max_files={max_files}, organize={organize}"
    )

    # Scan folder for files
    files = _batch_processor.scan_folder(folder_path, recursive=recursive)

    # Limit files if max_files specified
    if max_files and len(files) > max_files:
        logger.info(f"Limiting to {max_files} files (found {len(files)})")
        files = files[:max_files]

    # Track statistics
    stats = {
        "total_files": len(files),
        "successful": 0,
        "failed": 0,
        "ocr_processed": 0,
        "vision_processed": 0,
        "total_time_ms": 0.0,
        "average_time_per_file_ms": 0.0,
        "categories_count": {},
        "errors": [],
        "processed_files": []
    }

    start_time = time.perf_counter()

    # Process each file
    for file_path in files:
        try:
            # Analyze screenshot
            result = analyze_screenshot(str(file_path))
            stats["successful"] += 1

            # Update method counts
            if result["processing_method"] == "ocr":
                stats["ocr_processed"] += 1
            elif result["processing_method"] == "vision":
                stats["vision_processed"] += 1

            # Update category counts
            category = result["category"]
            stats["categories_count"][category] = stats["categories_count"].get(category, 0) + 1

            # Track processed file details
            processed_file = {
                "path": str(file_path),
                "category": category,
                "new_filename": result["suggested_filename"],
                "method": result["processing_method"]
            }
            stats["processed_files"].append(processed_file)

            # Organize if requested
            if organize:
                organize_result = _file_organizer.organize_file(
                    file_path,
                    category,
                    result["suggested_filename"]
                )
                if organize_result.success:
                    processed_file["organized_path"] = str(organize_result.destination_path)
                    logger.debug(f"Organized {file_path.name} to {organize_result.destination_path}")

        except Exception as e:
            stats["failed"] += 1
            error_entry = {
                "file_path": str(file_path),
                "error_message": str(e)
            }
            stats["errors"].append(error_entry)
            logger.error(f"Failed to process {file_path}: {e}")

    # Calculate timing statistics
    stats["total_time_ms"] = (time.perf_counter() - start_time) * 1000
    if stats["successful"] > 0:
        stats["average_time_per_file_ms"] = stats["total_time_ms"] / stats["successful"]

    logger.info(
        f"Batch processing complete: {stats['successful']}/{stats['total_files']} successful "
        f"in {stats['total_time_ms']:.2f}ms"
    )

    return stats


def organize_file(
    source_path: Annotated[str, Field(description="Current path of the file to organize")],
    category: Annotated[str, Field(description="Category for organization: code, errors, documentation, design, communication, memes, or other")],
    new_filename: Annotated[str, Field(description="New filename for the file (without extension)")],
    archive_original: Annotated[bool, Field(description="Keep a copy of the original file in archive")] = False,
    base_path: Annotated[Optional[str], Field(description="Base path for organized files (overrides default)")] = None
) -> Dict[str, Any]:
    """Move and rename a screenshot file to its category folder.

    Creates the category folder if it doesn't exist, moves the file, and
    renames it with a descriptive name. Optionally keeps a copy of the
    original file in an archive folder.

    Args:
        source_path: Current path of the file to organize
        category: Category folder (code, errors, documentation, design, communication, memes, other)
        new_filename: New filename without extension (extension preserved from original)
        archive_original: If True, keep a copy in archive folder
        base_path: Custom base path for organized files (overrides config default)

    Returns:
        Dictionary containing:
        - success: Whether the operation succeeded
        - original_path: Original file path
        - destination_path: New file path after organization
        - archived: Whether original was archived
        - error: Error message if failed (None if successful)
    """
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    logger.info(
        f"Organizing file: {source.name} → category={category}, "
        f"new_filename={new_filename}, archive={archive_original}"
    )

    # Create organizer with custom base path if provided
    if base_path:
        organizer = FileOrganizer(
            base_path,
            _file_organizer.categories,
            archive_original
        )
    else:
        organizer = _file_organizer

    # Organize file
    result = organizer.organize_file(source, category, new_filename)

    # Build response
    response = {
        "success": result.success,
        "original_path": str(result.original_path),
        "destination_path": str(result.destination_path) if result.destination_path else None,
        "archived": result.archived,
        "error": result.error
    }

    if result.success:
        logger.info(f"Successfully organized {source.name} to {result.destination_path}")
    else:
        logger.error(f"Failed to organize {source.name}: {result.error}")

    return response


# Internal helper functions

def _process_with_vision(path: Path) -> Dict[str, Any]:
    """Process screenshot with vision model.

    Args:
        path: Path to screenshot file.

    Returns:
        Dictionary with vision processing results.
    """
    vision_result = _vision_processor.process(path)

    return {
        "category": vision_result.category,
        "suggested_filename": vision_result.suggested_filename,
        "description": vision_result.description,
        "processing_method": "vision",
        "confidence_score": vision_result.confidence
    }


def _generate_filename_from_text(text: str, category: str) -> str:
    """Generate a descriptive filename from extracted text.

    Args:
        text: Extracted text from screenshot.
        category: Classified category.

    Returns:
        Suggested filename (without extension).
    """
    # Take first meaningful words (up to 5)
    words = [w for w in text.split() if len(w) > 2][:5]
    if words:
        return "_".join(words).lower()
    return f"{category}_screenshot"


def _generate_description_from_text(text: str) -> str:
    """Generate a brief description from extracted text.

    Args:
        text: Extracted text from screenshot.

    Returns:
        Brief description (1-2 sentences).
    """
    # Take first 100 characters as description
    description = text.strip()[:100]
    if len(text) > 100:
        description += "..."
    return description


# Legacy class for backward compatibility with existing code
class MCPToolHandlers:
    """Legacy class wrapper for backward compatibility.

    New code should use the standalone functions directly.
    This class is maintained for existing tests and code that hasn't been migrated yet.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize tool handlers (no-op for compatibility)."""
        # Expose module-level processors for test access
        self.ocr_processor = _ocr_processor
        self.vision_processor = _vision_processor
        self.classifier = _classifier
        self.file_organizer = _file_organizer
        self.batch_processor = _batch_processor
        logger.info("MCPToolHandlers initialized (legacy compatibility mode)")

    def analyze_screenshot(self, path: str, force_vision: bool = False) -> Dict[str, Any]:
        """Legacy wrapper for analyze_screenshot function."""
        return analyze_screenshot(path, force_vision)

    def batch_process(
        self,
        folder: str,
        recursive: bool = False,
        max_files: Optional[int] = None,
        organize: bool = False
    ) -> Dict[str, Any]:
        """Legacy wrapper for batch_process function."""
        return batch_process(folder, recursive, max_files, organize)

    def organize_file(
        self,
        source_path: str,
        category: str,
        new_filename: str,
        archive_original: bool = False,
        base_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Legacy wrapper for organize_file function."""
        return organize_file(source_path, category, new_filename, archive_original, base_path)
