"""Get list of available screenshot categories.

Returns category configuration for the Agent to use when categorizing.
"""

from typing import Any, Dict

from utils.logger import get_logger
from .shared import classifier, categories

logger = get_logger(__name__)


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
    patterns = classifier.patterns

    category_list = []
    for category_name in categories:
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

        category_list.append(category_info)

    return {
        "categories": category_list,
        "default_category": "other"
    }
