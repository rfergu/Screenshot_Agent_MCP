"""Suggest category based on text content using keyword matching.

This is a simple keyword-based fallback classifier. The Agent (GPT-4)
should make the final categorization decision using its intelligence.
"""

from typing import Annotated, Any, Dict, List

from pydantic import Field

from utils.logger import get_logger
from .shared import classifier

logger = get_logger(__name__)


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
    category = classifier.classify(text)

    # Find which keywords matched (simplified - just check if category keywords appear in text)
    patterns = classifier.patterns
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
