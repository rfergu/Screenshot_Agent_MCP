"""OCR Processor using Tesseract for text extraction from images."""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pytesseract
from PIL import Image

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class OCRResult:
    """Result from OCR processing."""
    text: str
    word_count: int
    processing_time_ms: float
    sufficient_text: bool
    language: str = "en"
    confidence: float = 0.0


class OCRProcessor:
    """Handles OCR processing using Tesseract."""

    def __init__(self, min_words_threshold: int = 10):
        """Initialize OCR processor.

        Args:
            min_words_threshold: Minimum word count to consider text sufficient
                for classification without needing vision model.
        """
        self.min_words_threshold = min_words_threshold
        logger.info(f"OCRProcessor initialized with min_words_threshold={min_words_threshold}")

    def process(self, image_path: str | Path) -> OCRResult:
        """Extract text from image using OCR.

        Args:
            image_path: Path to the image file to process.

        Returns:
            OCRResult with extracted text and metadata.

        Raises:
            FileNotFoundError: If image file doesn't exist.
            Exception: If OCR processing fails.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        logger.debug(f"Processing image with OCR: {image_path}")
        start_time = time.perf_counter()

        try:
            # Open and process image
            with Image.open(image_path) as img:
                # Extract text using Tesseract
                text = pytesseract.image_to_string(img, lang="eng")

            # Calculate metrics
            processing_time_ms = (time.perf_counter() - start_time) * 1000
            word_count = len(text.split())
            sufficient_text = word_count >= self.min_words_threshold

            logger.info(
                f"OCR complete: {word_count} words in {processing_time_ms:.2f}ms "
                f"(sufficient={sufficient_text})"
            )

            return OCRResult(
                text=text.strip(),
                word_count=word_count,
                processing_time_ms=processing_time_ms,
                sufficient_text=sufficient_text,
                language="en",
                confidence=0.0,  # Tesseract confidence not easily accessible
            )

        except Exception as e:
            processing_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"OCR processing failed after {processing_time_ms:.2f}ms: {e}")
            raise

    def process_with_preprocessing(self, image_path: str | Path) -> OCRResult:
        """Process image with preprocessing for better OCR accuracy.

        Args:
            image_path: Path to the image file to process.

        Returns:
            OCRResult with extracted text and metadata.
        """
        # TODO: Add image preprocessing (grayscale, threshold, denoise)
        # For now, just use standard processing
        return self.process(image_path)
