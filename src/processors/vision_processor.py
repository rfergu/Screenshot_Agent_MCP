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

        Note: phi-3-vision-mlx v0.0.3rc1 has a syntax error at line 699.
        We work around this by reading, patching, and executing the module code.
        """
        if self.model is None:
            logger.info("Loading Phi-3 Vision model (this may take a moment)...")
            try:
                # Workaround for phi-3-vision-mlx v0.0.3rc1 syntax error
                import sys
                from pathlib import Path as PathLib

                # Find the phi_3_vision_mlx.py file
                phi3_module_path = None
                for path in sys.path:
                    candidate = PathLib(path) / "phi_3_vision_mlx.py"
                    if candidate.exists():
                        phi3_module_path = candidate
                        break

                if not phi3_module_path:
                    raise ImportError("phi-3-vision-mlx module file not found")

                # Read and patch the syntax error
                with open(phi3_module_path, 'r') as f:
                    module_code = f.read()

                # Fix line 699: Replace nested quotes in f-string
                # Original: {textwrap.indent(code, "    ")}
                # Fixed: {textwrap.indent(code, '    ')}
                module_code = module_code.replace(
                    'textwrap.indent(code, "    ")',
                    "textwrap.indent(code, '    ')"
                )

                # Create namespace and execute patched code
                phi3_namespace = {'__name__': 'phi_3_vision_mlx'}
                exec(module_code, phi3_namespace)

                # Store the chat function
                self.model = {
                    'chat': phi3_namespace['chat'],
                    '_preload': phi3_namespace.get('_preload'),
                    '_apply_chat_template': phi3_namespace.get('_apply_chat_template'),
                    'generate': phi3_namespace.get('generate')
                }
                logger.info("Phi-3 Vision model loaded successfully (patched v0.0.3rc1)")

            except FileNotFoundError:
                logger.error("phi-3-vision-mlx module not found")
                raise ImportError(
                    "phi-3-vision-mlx not available. Install with: pip install phi-3-vision-mlx"
                )
            except Exception as e:
                logger.error(f"Failed to load Phi-3 Vision model: {e}", exc_info=True)
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
            Model response as string (JSON format expected).
        """
        try:
            # Call the phi-3-vision-mlx chat function
            # chat(prompt, images=None, preload=None, max_tokens=500, ...)
            response_tuple = self.model['chat'](
                prompt=self.prompt_template,
                images=[image],
                max_tokens=500,
                verbose=False,
                stream=False
            )

            # chat() returns a tuple: (response_text, ...)
            if isinstance(response_tuple, tuple):
                response_text = response_tuple[0]
            else:
                response_text = str(response_tuple)

            logger.debug(f"Vision model raw response: {response_text[:200]}...")
            return response_text

        except Exception as e:
            logger.error(f"Error calling vision model: {e}", exc_info=True)
            # Return a safe fallback
            return '{"category": "other", "description": "Vision model error", "filename": "error_processing"}'

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
