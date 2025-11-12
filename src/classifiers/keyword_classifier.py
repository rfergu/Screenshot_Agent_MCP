"""Keyword-based classifier for screenshot categorization."""

import re
from typing import Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class KeywordClassifier:
    """Classifies screenshots based on keyword patterns in extracted text."""

    def __init__(self, custom_patterns: Optional[Dict[str, List[str]]] = None):
        """Initialize classifier with default or custom patterns.

        Args:
            custom_patterns: Optional dictionary of category -> keyword patterns.
                           If provided, replaces default patterns.
        """
        if custom_patterns:
            self.patterns = custom_patterns
            logger.info(f"KeywordClassifier initialized with custom patterns: {list(custom_patterns.keys())}")
        else:
            # Default patterns based on research.md classification patterns
            self.patterns = {
                "code": [
                    r'\bdef\s+\w+',  # Python functions
                    r'\bclass\s+\w+',  # Class definitions
                    r'\bfunction\s+\w+',  # JavaScript functions
                    r'\bimport\s+',  # Import statements
                    r'\bfrom\s+\w+\s+import',  # Python imports
                    r'\bconst\s+\w+\s*=',  # JavaScript const
                    r'\blet\s+\w+\s*=',  # JavaScript let
                    r'\bvar\s+\w+\s*=',  # JavaScript var
                    r'\bpublic\s+class',  # Java class
                    r'\bprivate\s+\w+',  # Java/C++ private
                    r'<\?php',  # PHP code
                    r'#include\s+<',  # C/C++ includes
                    r'\breturn\s+\w+',  # Return statements
                    r'\bif\s*\(',  # Conditional statements
                    r'\bfor\s*\(',  # For loops
                    r'\bwhile\s*\(',  # While loops
                ],
                "errors": [
                    r'\berror\b',
                    r'\bexception\b',
                    r'\bfailed\b',
                    r'\bwarning\b',
                    r'\btraceback\b',
                    r'\bstack trace\b',
                    r'\bsyntaxerror\b',
                    r'\bnameerror\b',
                    r'\btypeerror\b',
                    r'\bvalueerror\b',
                    r'\bcritical\b',
                    r'\bfatal\b',
                    r'\bpanic\b',
                    r'\bsegmentation fault\b',
                    r'\bnullpointerexception\b',
                    r'\bundefined\s+reference',
                ],
                "documentation": [
                    r'\bapi\s+reference\b',
                    r'\bdocumentation\b',
                    r'\btutorial\b',
                    r'\bguide\b',
                    r'\bhow\s+to\b',
                    r'\breadme\b',
                    r'\bchangelog\b',
                    r'\brelease\s+notes\b',
                    r'\binstallation\b',
                    r'\bquickstart\b',
                    r'\bexample\b',
                    r'\busage\b',
                    r'\bgetting\s+started\b',
                ],
                "design": [
                    r'\bmockup\b',
                    r'\bwireframe\b',
                    r'\bprototype\b',
                    r'\bui\s+design\b',
                    r'\bux\s+design\b',
                    r'\bfigma\b',
                    r'\bsketch\b',
                    r'\bdesign\s+system\b',
                    r'\bcolor\s+palette\b',
                    r'\btypography\b',
                    r'\blayout\b',
                ],
                "communication": [
                    r'\bslack\b',
                    r'\bdiscord\b',
                    r'\bteams\b',
                    r'\bemail\b',
                    r'\bmessage\b',
                    r'\bchat\b',
                    r'\bconversation\b',
                    r'\bmeeting\b',
                    r'\bnotification\b',
                    r'\bdm\b',
                    r'\breply\b',
                    r'\bcomment\b',
                ],
                "memes": [
                    r'\bmeme\b',
                    r'\blol\b',
                    r'\blmao\b',
                    r'\brofl\b',
                    r'\bhaha\b',
                    r'\bfunny\b',
                    r'\bjoke\b',
                    r'\bsarcasm\b',
                    r'😂',
                    r'🤣',
                    r'💀',
                ],
            }
            logger.info(f"KeywordClassifier initialized with default patterns: {list(self.patterns.keys())}")

        # Compile regex patterns for efficiency
        self.compiled_patterns = {
            category: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for category, patterns in self.patterns.items()
        }

    def classify(self, text: str) -> str:
        """Classify text based on keyword patterns.

        Args:
            text: Text to classify (typically from OCR).

        Returns:
            Category string: one of code, errors, documentation, design,
                           communication, memes, or other.
        """
        if not text or not text.strip():
            logger.debug("Empty text provided, returning 'other'")
            return "other"

        # Count matches for each category
        category_scores: Dict[str, int] = {category: 0 for category in self.patterns.keys()}

        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                matches = pattern.findall(text)
                if matches:
                    category_scores[category] += len(matches)
                    logger.debug(f"Found {len(matches)} matches for '{pattern.pattern}' in category '{category}'")

        # Find category with highest score
        if max(category_scores.values()) > 0:
            best_category = max(category_scores.items(), key=lambda x: x[1])[0]
            logger.info(f"Classified as '{best_category}' with {category_scores[best_category]} matches")
            return best_category
        else:
            logger.info("No keyword matches found, returning 'other'")
            return "other"

    def get_categories(self) -> List[str]:
        """Get list of available categories.

        Returns:
            List of category names.
        """
        return list(self.patterns.keys()) + ["other"]

    def add_pattern(self, category: str, pattern: str):
        """Add a new keyword pattern to a category.

        Args:
            category: Category to add pattern to (must exist or will be created).
            pattern: Regex pattern string to add.
        """
        if category not in self.patterns:
            logger.info(f"Creating new category: {category}")
            self.patterns[category] = []
            self.compiled_patterns[category] = []

        self.patterns[category].append(pattern)
        self.compiled_patterns[category].append(re.compile(pattern, re.IGNORECASE))
        logger.info(f"Added pattern '{pattern}' to category '{category}'")
