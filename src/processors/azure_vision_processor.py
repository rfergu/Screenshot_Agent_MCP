"""Azure Vision Processor using GPT-4o for image understanding."""

import base64
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from PIL import Image
from openai import AzureOpenAI

from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class VisionResult:
    """Result from Azure GPT-4o Vision processing."""
    category: str
    description: str
    suggested_filename: str
    processing_time_ms: float
    raw_response: str
    confidence: float = 0.8  # GPT-4o is generally high confidence


class AzureVisionProcessor:
    """Handles vision processing using Azure OpenAI GPT-4o."""

    def __init__(self):
        """Initialize Azure vision processor with lazy client creation."""
        self.client = None
        self.deployment = None
        self.prompt_template = """Analyze this screenshot and determine:
1. Category: code, errors, documentation, design, communication, memes, or other
2. Main content description (brief, 1-2 sentences)
3. Suggested filename (descriptive, no spaces, lowercase with underscores)

Return ONLY valid JSON in this exact format:
{"category": "code", "description": "Brief description here", "filename": "descriptive_name_here"}

Categories must be one of: code, errors, documentation, design, communication, memes, other"""

        logger.info("AzureVisionProcessor initialized (client will connect on first use)")

    def ensure_client_ready(self):
        """Lazy initialize Azure OpenAI client on first use."""
        if self.client is None:
            # Get Azure OpenAI credentials from environment
            # Support both AZURE_OPENAI_ENDPOINT and AZURE_AI_CHAT_ENDPOINT
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("AZURE_AI_CHAT_ENDPOINT")
            api_key = os.getenv("AZURE_AI_CHAT_KEY")
            deployment = os.getenv("AZURE_AI_MODEL_DEPLOYMENT", "gpt-4o")
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

            if not endpoint or not api_key:
                raise ValueError(
                    "Azure OpenAI credentials not found. "
                    "Set AZURE_OPENAI_ENDPOINT (or AZURE_AI_CHAT_ENDPOINT) and AZURE_AI_CHAT_KEY environment variables."
                )

            self.client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=api_version
            )
            self.deployment = deployment
            logger.info(f"Azure OpenAI client initialized successfully (deployment: {deployment})")

    def process(self, image_path: str | Path) -> VisionResult:
        """Process image using Azure GPT-4o Vision.

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

        logger.debug(f"Processing image with Azure GPT-4o Vision: {image_path}")
        start_time = time.perf_counter()

        try:
            # Ensure client is ready
            self.ensure_client_ready()

            # Encode image to base64
            with open(image_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')

            # Determine image format
            image_format = image_path.suffix.lower().lstrip('.')
            if image_format == 'jpg':
                image_format = 'jpeg'

            # Call Azure OpenAI GPT-4o with vision
            response = self.client.chat.completions.create(
                model=self.deployment,  # Use configured deployment name
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": self.prompt_template
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{image_format};base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500,
                temperature=0.3  # Lower temperature for more consistent categorization
            )

            # Extract response
            response_text = response.choices[0].message.content
            logger.debug(f"GPT-4o Vision response: {response_text[:200]}...")

            # Parse JSON response
            parsed = self._parse_response(response_text)

            processing_time_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                f"Azure vision processing complete: {parsed['category']} "
                f"in {processing_time_ms:.2f}ms"
            )

            return VisionResult(
                category=parsed["category"],
                description=parsed["description"],
                suggested_filename=parsed["filename"],
                processing_time_ms=processing_time_ms,
                raw_response=response_text,
                confidence=0.8
            )

        except Exception as e:
            processing_time_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"Azure vision processing failed after {processing_time_ms:.2f}ms: {e}")
            raise

    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse JSON response from GPT-4o Vision.

        Args:
            response: Raw model response string.

        Returns:
            Parsed response dictionary with category, description, filename.

        Raises:
            ValueError: If response is not valid JSON or missing required fields.
        """
        try:
            # Try to extract JSON from response (GPT-4o sometimes adds markdown)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.startswith("```"):
                response = response[3:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

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
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Raw response: {response}")
            raise ValueError(f"Invalid JSON response from vision model: {e}")
