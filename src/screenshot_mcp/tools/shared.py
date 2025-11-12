"""Shared processors and utilities for MCP tools.

This module initializes all processors and organizers at module level
so they can be imported by individual tool modules without duplication.
"""

from classifiers.keyword_classifier import KeywordClassifier
from organizers.batch_processor import BatchProcessor
from organizers.file_organizer import FileOrganizer
from processors.ocr_processor import OCRProcessor
from processors.azure_vision_processor import AzureVisionProcessor
from utils.config import get as config_get
from utils.logger import get_logger

logger = get_logger(__name__)

# Initialize processors and organizers at module level
ocr_min_words = config_get("processing.ocr_min_words", 10)
ocr_processor = OCRProcessor(min_words_threshold=ocr_min_words)
vision_processor = AzureVisionProcessor()
classifier = KeywordClassifier()

base_folder = config_get("organization.base_folder", "~/Screenshots/organized")
categories = config_get("organization.categories", ["code", "errors", "documentation", "design", "communication", "memes", "other"])
keep_originals = config_get("organization.keep_originals", True)
file_organizer = FileOrganizer(base_folder, categories, keep_originals)

batch_processor = BatchProcessor()

logger.info("MCP tools shared processors initialized")
