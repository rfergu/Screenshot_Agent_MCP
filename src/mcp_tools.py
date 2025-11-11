"""MCP tool handlers implementing screenshot analysis and organization logic."""

import time
from pathlib import Path
from typing import Any, Dict, Optional

from classifiers.keyword_classifier import KeywordClassifier
from organizers.batch_processor import BatchProcessor, FileProcessingResult
from organizers.file_organizer import FileOrganizer
from processors.ocr_processor import OCRProcessor
from processors.vision_processor import VisionProcessor
from utils.config import get as config_get
from utils.logger import get_logger

logger = get_logger(__name__)


class MCPToolHandlers:
    """Handlers for MCP tools implementing tiered processing logic."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize tool handlers with processors and organizers.

        Args:
            config: Optional configuration dictionary. If None, uses default config.
        """
        # Initialize processors
        ocr_min_words = config_get("processing.ocr_min_words", 10) if config is None else config.get("ocr_min_words", 10)
        self.ocr_processor = OCRProcessor(min_words_threshold=ocr_min_words)
        self.vision_processor = VisionProcessor()
        self.classifier = KeywordClassifier()

        # Initialize organizer
        base_folder = config_get("organization.base_folder", "~/Screenshots/organized")
        categories = config_get("organization.categories", ["code", "errors", "documentation", "design", "communication", "memes", "other"])
        keep_originals = config_get("organization.keep_originals", True)
        self.file_organizer = FileOrganizer(base_folder, categories, keep_originals)

        # Initialize batch processor
        self.batch_processor = BatchProcessor()

        logger.info("MCPToolHandlers initialized with all processors and organizers")

    def analyze_screenshot(
        self,
        path: str,
        force_vision: bool = False
    ) -> Dict[str, Any]:
        """Analyze a screenshot using tiered OCR → keyword → vision approach.

        Args:
            path: Absolute path to the screenshot file.
            force_vision: If True, skip OCR and use vision model directly.

        Returns:
            Dictionary with category, suggested_filename, description,
            processing_method, processing_time_ms, and other analysis results.
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
                response.update(self._process_with_vision(path_obj))
            else:
                # Tiered approach: OCR → keyword classification → vision if needed
                logger.debug("Starting tiered approach: OCR first")
                ocr_result = self.ocr_processor.process(path_obj)
                response["extracted_text"] = ocr_result.text

                if ocr_result.sufficient_text:
                    # OCR extracted enough text, classify it
                    logger.debug(f"Sufficient text found ({ocr_result.word_count} words), classifying")
                    category = self.classifier.classify(ocr_result.text)
                    
                    response.update({
                        "category": category,
                        "suggested_filename": self._generate_filename_from_text(ocr_result.text, category),
                        "description": self._generate_description_from_text(ocr_result.text),
                        "processing_method": "ocr",
                        "confidence_score": 0.8  # High confidence for text-based classification
                    })
                else:
                    # Insufficient text, fall back to vision
                    logger.debug(f"Insufficient text ({ocr_result.word_count} words), falling back to vision")
                    response.update(self._process_with_vision(path_obj))

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

    def _process_with_vision(self, path: Path) -> Dict[str, Any]:
        """Process screenshot with vision model.

        Args:
            path: Path to screenshot file.

        Returns:
            Dictionary with vision processing results.
        """
        vision_result = self.vision_processor.process(path)

        return {
            "category": vision_result.category,
            "suggested_filename": vision_result.suggested_filename,
            "description": vision_result.description,
            "processing_method": "vision",
            "confidence_score": vision_result.confidence
        }

    def _generate_filename_from_text(self, text: str, category: str) -> str:
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

    def _generate_description_from_text(self, text: str) -> str:
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

    def batch_process(
        self,
        folder: str,
        recursive: bool = False,
        max_files: Optional[int] = None,
        organize: bool = False
    ) -> Dict[str, Any]:
        """Process all screenshots in a folder.

        Args:
            folder: Path to the folder containing screenshots.
            recursive: Process subfolders recursively.
            max_files: Maximum number of files to process.
            organize: Automatically organize files after analysis.

        Returns:
            Dictionary with batch processing statistics and results.
        """
        folder_path = Path(folder)
        if not folder_path.exists():
            raise FileNotFoundError(f"Folder not found: {folder}")

        logger.info(
            f"Starting batch processing: folder={folder}, recursive={recursive}, "
            f"max_files={max_files}, organize={organize}"
        )

        # Scan folder for files
        files = self.batch_processor.scan_folder(folder_path, recursive=recursive)

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
                result = self.analyze_screenshot(str(file_path))
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
                    organize_result = self.file_organizer.organize_file(
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
        self,
        source_path: str,
        category: str,
        new_filename: str,
        archive_original: bool = False,
        base_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Move and rename a screenshot file based on its category.

        Args:
            source_path: Current path of the file to organize.
            category: Category for organization.
            new_filename: New filename for the file (without extension).
            archive_original: Keep a copy of the original file in archive.
            base_path: Base path for organized files.

        Returns:
            Dictionary with organization result details.
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
                self.file_organizer.categories,
                archive_original
            )
        else:
            organizer = self.file_organizer

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
