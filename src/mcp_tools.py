"""Low-level file operation tools for MCP server subprocess.

Architecture: These tools are provided by the MCP SERVER in the unified architecture:
  Agent Framework (Brain) → makes decisions
  MCP Client Wrapper (embedded) → protocol bridge
  MCP Server (subprocess) → provides THESE TOOLS
  File System → accessed via these tools

Tool Philosophy - "Dumb Tools, Smart Agent":
- Tools return FACTS and DATA (not decisions)
- Tools execute FILE OPERATIONS (no intelligence)
- Agent Framework (GPT-4) makes INTELLIGENT DECISIONS:
  * Categorization (based on content understanding)
  * Descriptive filenames (creative, context-aware)
  * Workflow orchestration (multi-step operations)

This demonstrates separation of concerns in Agent Framework WITH MCP Client Integration.
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

from pydantic import Field

from classifiers.keyword_classifier import KeywordClassifier
from organizers.batch_processor import BatchProcessor
from organizers.file_organizer import FileOrganizer
from processors.ocr_processor import OCRProcessor
from processors.azure_vision_processor import AzureVisionProcessor
from utils.config import get as config_get
from utils.logger import get_logger

logger = get_logger(__name__)

# Initialize processors and organizers at module level
_ocr_min_words = config_get("processing.ocr_min_words", 10)
_ocr_processor = OCRProcessor(min_words_threshold=_ocr_min_words)
_vision_processor = AzureVisionProcessor()
_classifier = KeywordClassifier()

_base_folder = config_get("organization.base_folder", "~/Screenshots/organized")
_categories = config_get("organization.categories", ["code", "errors", "documentation", "design", "communication", "memes", "other"])
_keep_originals = config_get("organization.keep_originals", True)
_file_organizer = FileOrganizer(_base_folder, _categories, _keep_originals)

_batch_processor = BatchProcessor()

logger.info("Screenshot tools initialized with all processors and organizers")


# ============================================================================
# LOW-LEVEL FILE OPERATION TOOLS (for Agent Framework orchestration)
# ============================================================================

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
    files = _batch_processor.scan_folder(dir_path, recursive=recursive)

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
    # Normalize path by removing shell escape characters
    normalized_path = file_path.replace('\\ ', ' ')  # Handle escaped spaces from shell
    path_obj = Path(normalized_path).expanduser()
    if not path_obj.exists():
        raise FileNotFoundError(f"Screenshot file not found: {normalized_path}")

    logger.info(f"Analyzing screenshot: {file_path} (force_vision={force_vision})")
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
            vision_result = _vision_processor.process(path_obj)
            response.update({
                "vision_description": vision_result.description,
                "processing_method": "vision",
                "success": True
            })
        else:
            # Try OCR first
            logger.debug("Attempting OCR extraction")
            try:
                ocr_result = _ocr_processor.process(path_obj)
                response.update({
                    "extracted_text": ocr_result.text,
                    "word_count": ocr_result.word_count,
                    "processing_method": "ocr",
                    "success": True
                })

                # If insufficient text, add vision description
                if not ocr_result.sufficient_text:
                    logger.debug("Insufficient OCR text, adding vision analysis")
                    vision_result = _vision_processor.process(path_obj)
                    response["vision_description"] = vision_result.description
                    response["processing_method"] = "vision"

            except Exception as ocr_error:
                # OCR failed, fall back to vision processing
                logger.warning(f"OCR failed ({ocr_error}), falling back to vision model")
                vision_result = _vision_processor.process(path_obj)
                response.update({
                    "vision_description": vision_result.description,
                    "processing_method": "vision",
                    "success": True
                })

        response["processing_time_ms"] = (time.perf_counter() - start_time) * 1000

        logger.info(
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


def get_categories() -> Dict[str, Any]:
    """Get list of available screenshot categories.

    Returns category configuration for the Agent to use when categorizing.

    Returns:
        Dictionary containing:
        - categories: List of category dictionaries with name, description, keywords
        - default_category: Default category for uncategorized items
    """
    logger.debug("Getting category configuration")

    # Get keyword patterns from classifier
    patterns = _classifier.patterns

    categories = []
    for category_name in _categories:
        category_info = {
            "name": category_name,
            "keywords": patterns.get(category_name, [])
        }

        # Add descriptions based on category
        descriptions = {
            "code": "Code snippets, terminal output, IDE screenshots, programming content",
            "errors": "Error messages, stack traces, warnings, exceptions",
            "documentation": "Documentation pages, technical specs, API references",
            "design": "UI mockups, design files, graphics, visual assets",
            "communication": "Messages, emails, chat conversations, social media",
            "memes": "Memes, jokes, funny images",
            "other": "Miscellaneous screenshots that don't fit other categories"
        }
        category_info["description"] = descriptions.get(category_name, "")

        categories.append(category_info)

    return {
        "categories": categories,
        "default_category": "other"
    }


def categorize_screenshot(
    text: Annotated[str, Field(description="Text content to categorize")],
    available_categories: Annotated[List[str], Field(description="List of valid category names")] = None
) -> Dict[str, Any]:
    """Suggest category based on text content using keyword matching.

    This is a simple keyword-based fallback classifier. The Agent (GPT-4)
    should make the final categorization decision using its intelligence.

    Args:
        text: Text content to categorize
        available_categories: List of valid category names (optional)

    Returns:
        Dictionary containing:
        - suggested_category: Category name based on keyword matching
        - confidence: Confidence score (0.0-1.0)
        - matched_keywords: List of keywords that matched
        - method: Always "keyword_classifier"
    """
    logger.debug(f"Categorizing text using keyword classifier ({len(text)} chars)")

    # Use keyword classifier
    category = _classifier.classify(text)

    # Find which keywords matched (simplified - just check if category keywords appear in text)
    patterns = _classifier.patterns
    matched_keywords = []
    if category in patterns:
        text_lower = text.lower()
        matched_keywords = [kw for kw in patterns[category] if kw in text_lower]

    # Calculate simple confidence based on keyword matches
    confidence = 0.5  # Base confidence
    if matched_keywords:
        confidence = min(0.9, 0.5 + (len(matched_keywords) * 0.1))

    return {
        "suggested_category": category,
        "confidence": confidence,
        "matched_keywords": matched_keywords,
        "method": "keyword_classifier"
    }


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
        base = Path(_base_folder).expanduser()
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
    # Normalize paths by removing shell escape characters
    normalized_source = source_path.replace('\\ ', ' ')  # Handle escaped spaces from shell
    normalized_dest = dest_folder.replace('\\ ', ' ')  # Handle escaped spaces from shell

    source = Path(normalized_source).expanduser()
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


# ============================================================================
# LEGACY COMPATIBILITY (for existing code)
# ============================================================================

class MCPToolHandlers:
    """Legacy class wrapper for backward compatibility.

    New code should use the standalone low-level functions directly.
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

    def list_screenshots(self, directory: str, recursive: bool = False, max_files: Optional[int] = None) -> Dict[str, Any]:
        """Legacy wrapper for list_screenshots function."""
        return list_screenshots(directory, recursive, max_files)

    def analyze_screenshot(self, file_path: str, force_vision: bool = False) -> Dict[str, Any]:
        """Legacy wrapper for analyze_screenshot function."""
        return analyze_screenshot(file_path, force_vision)

    def get_categories(self) -> Dict[str, Any]:
        """Legacy wrapper for get_categories function."""
        return get_categories()

    def categorize_screenshot(self, text: str, available_categories: List[str] = None) -> Dict[str, Any]:
        """Legacy wrapper for categorize_screenshot function."""
        return categorize_screenshot(text, available_categories)

    def create_category_folder(self, category: str, base_dir: Optional[str] = None) -> Dict[str, Any]:
        """Legacy wrapper for create_category_folder function."""
        return create_category_folder(category, base_dir)

    def move_screenshot(
        self,
        source_path: str,
        dest_folder: str,
        new_filename: Optional[str] = None,
        keep_original: bool = True
    ) -> Dict[str, Any]:
        """Legacy wrapper for move_screenshot function."""
        return move_screenshot(source_path, dest_folder, new_filename, keep_original)

    def generate_filename(
        self,
        original_filename: str,
        category: str,
        text: Optional[str] = None,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """Legacy wrapper for generate_filename function."""
        return generate_filename(original_filename, category, text, description)
