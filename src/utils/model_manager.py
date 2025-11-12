"""Simple system requirements checker for Screenshot Organizer.

This module checks if required system dependencies are available.
Note: Model downloading and caching functionality removed as it was not implemented.
"""

from typing import Dict, List
from utils.logger import get_logger

logger = get_logger(__name__)


def check_tesseract() -> bool:
    """Check if Tesseract OCR is available.

    Returns:
        True if Tesseract is installed and accessible.
    """
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        logger.debug(f"Tesseract OCR version {version} found")
        return True
    except Exception as e:
        logger.debug(f"Tesseract OCR not available: {e}")
        return False


def check_foundry_cli() -> bool:
    """Check if Azure AI Foundry CLI is available.

    Returns:
        True if foundry CLI is installed.
    """
    import subprocess
    try:
        result = subprocess.run(
            ['foundry', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            logger.debug("Azure AI Foundry CLI found")
            return True
        return False
    except (FileNotFoundError, subprocess.TimeoutExpired):
        logger.debug("Azure AI Foundry CLI not found")
        return False
    except Exception as e:
        logger.debug(f"Error checking Foundry CLI: {e}")
        return False


def check_requirements() -> Dict[str, any]:
    """Check all system requirements.

    Returns:
        Dictionary with requirement check results:
        {
            'all_required_available': bool,
            'requirements': {
                'tesseract': {'available': bool, 'required': bool, 'name': str, 'install': str},
                'foundry_cli': {...}
            }
        }
    """
    requirements = {
        'tesseract': {
            'available': check_tesseract(),
            'required': True,
            'name': 'Tesseract OCR',
            'install': 'macOS: brew install tesseract | Linux: apt-get install tesseract-ocr'
        },
        'foundry_cli': {
            'available': check_foundry_cli(),
            'required': False,  # Only needed for local mode
            'name': 'Azure AI Foundry CLI',
            'install': 'brew install azure/ai-foundry/foundry'
        }
    }

    # Check if all required dependencies are available
    all_required_available = all(
        info['available']
        for info in requirements.values()
        if info['required']
    )

    return {
        'all_required_available': all_required_available,
        'requirements': requirements
    }


def suggest_actions() -> List[str]:
    """Suggest installation actions for missing requirements.

    Returns:
        List of suggested action messages.
    """
    suggestions = []
    check_results = check_requirements()

    for key, info in check_results['requirements'].items():
        if not info['available']:
            if info['required']:
                suggestions.append(f"REQUIRED: Install {info['name']}")
                suggestions.append(f"  → {info['install']}")
            else:
                suggestions.append(f"OPTIONAL: Install {info['name']} for local mode")
                suggestions.append(f"  → {info['install']}")

    return suggestions
