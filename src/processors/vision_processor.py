"""Vision Processor using Phi-3 Vision MLX for image understanding."""

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from PIL import Image

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VisionResult:
    """Result from Phi-3 Vision processing."""
    category: str
    description: str
    suggested_filename: str
    processing_time_ms: float
    raw_response: str
    confidence: float = 0.0


class VisionProcessor:
    """Handles vision model processing using Phi-3 Vision MLX."""

    def __init__(self):
        """Initialize vision processor with lazy model loading."""
        self.model = None
        self.prompt_template = """
Analyze this screenshot and determine:
1. Category: code, errors, documentation, design, communication, memes, or other
2. Main content description (brief, 1-2 sentences)
3. Suggested filename (descriptive, no spaces, lowercase with underscores)

Return ONLY valid JSON in this exact format:
{"category": "code", "description": "Brief description here", "filename": "descriptive_name_here"}

Categories must be one of: code, errors, documentation, design, communication, memes, other
"""
        logger.info("VisionProcessor initialized (model will load on first use)")

    def ensure_model_loaded(self):
        """Lazy load Phi-3 Vision model on first use.

        This defers the expensive model loading (~8GB) until actually needed.
        """
        if self.model is None:
            logger.info("Loading Phi-3 Vision model (this may take a moment)...")
            try:
                # Import here to avoid requiring phi-3-vision-mlx if not used
                from phi3v import Phi3Vision
                self.model = Phi3Vision()
                logger.info("Phi-3 Vision model loaded successfully")
            except ImportError as e:
                logger.error(f"Failed to import phi-3-vision-mlx: {e}")
                raise ImportError(
                    "phi-3-vision-mlx not available. Install with: pip install phi-3-vision-mlx"
                ) from e
            except Exception as e:
                logger.error(f"Failed to load Phi-3 Vision model: {e}")
                raise

    def process(self, image_path: str | Path) -> VisionResult:
        """Process image using Phi-3 Vision model.

        Args:
            image_path: Path to the image file to analyze.

        Returns:
            VisionResult with category, description, and filename suggestion.

        Raises:
            FileNotFoundError: If image file doesn't exist.
            Exception: If vision processing fails.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        logger.debug(f"Processing image with vision model: {image_path}")
        start_time = time.perf_counter()

        try:
            # Ensure model is loaded
            self.ensure_model_loaded()

            # Open image
            with Image.open(image_path) as img:
                # Get response from model
                # Note: Actual phi-3-vision-mlx API may differ
                # This is a placeholder implementation
                response = self._call_model(img)

            # Parse JSON response
            result_data = self._parse_response(response)

            processing_time_ms = (time.perf_counter() - start_time) * 1000

            logger.info(
                f"Vision processing complete: category={result_data['category']} "
                f"in {processing_time_ms:.2f}ms"
            )

            return VisionResult(
                category=result_data["category"],
                description=result_data["description"],
                suggested_filename=result_data["filename"],
                processing_time_ms=processing_time_ms,
                raw_response=response,
                confidence=0.0,  # TODO: Extract confidence from model if available
            )

        except Exception as e:
            processing_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Vision processing failed after {processing_time_ms:.2f}ms: {e}")
            raise

    def _call_model(self, image: Image.Image) -> str:
        """Call Phi-3 Vision model with image and prompt.

        Args:
            image: PIL Image to process.

        Returns:
            Model response as string.
        """
        # TODO: Implement actual model call when phi-3-vision-mlx is available
        # For now, return a placeholder that will be replaced with real model call
        logger.warning("Using placeholder model response (real model not implemented yet)")
        return '{"category": "other", "description": "Placeholder response", "filename": "placeholder"}'

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response from vision model.

        Args:
            response: Raw model response string.

        Returns:
            Parsed response dictionary with category, description, filename.

        Raises:
            ValueError: If response is not valid JSON or missing required fields.
        """
        try:
            data = json.loads(response)
            
            # Validate required fields
            required_fields = ["category", "description", "filename"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")

            # Validate category
            valid_categories = ["code", "errors", "documentation", "design", 
                              "communication", "memes", "other"]
            if data["category"] not in valid_categories:
                logger.warning(
                    f"Invalid category '{data['category']}', defaulting to 'other'"
                )
                data["category"] = "other"

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse vision model response as JSON: {e}")
            raise ValueError(f"Invalid JSON response from vision model: {response}") from e
