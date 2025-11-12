"""Foundry Local endpoint detection utilities.

This module helps auto-detect the Azure AI Foundry Local service endpoint,
which uses a dynamically-allocated port that changes on each service start.
"""

import re
import subprocess
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)

# Cache for session duration (avoid running subprocess repeatedly)
_cached_endpoint: Optional[str] = None


def detect_foundry_endpoint() -> Optional[str]:
    """Auto-detect Foundry Local service endpoint via 'foundry service status'.

    The Foundry Local service uses a dynamically-allocated port, so we need to
    detect it at runtime. This function:
    1. Runs 'foundry service status' subprocess
    2. Parses output for endpoint URL (e.g., http://127.0.0.1:60779/openai/status)
    3. Converts to chat completions endpoint format

    Returns:
        Chat completions endpoint URL, or None if detection fails.

    Example:
        >>> endpoint = detect_foundry_endpoint()
        >>> print(endpoint)
        http://127.0.0.1:60779/v1/chat/completions
    """
    global _cached_endpoint

    # Return cached value if available
    if _cached_endpoint is not None:
        logger.debug(f"Using cached Foundry endpoint: {_cached_endpoint}")
        return _cached_endpoint

    try:
        # Run foundry service status
        logger.debug("Running 'foundry service status' to detect endpoint...")
        result = subprocess.run(
            ["foundry", "service", "status"],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            logger.warning(f"'foundry service status' failed with code {result.returncode}")
            logger.debug(f"stderr: {result.stderr}")
            return None

        output = result.stdout
        logger.debug(f"foundry service status output: {output}")

        # Parse endpoint from output
        # Expected format: "Model management service is running on http://127.0.0.1:60779/openai/status"
        # We want to extract: http://127.0.0.1:60779
        match = re.search(r'http://127\.0\.0\.1:\d+', output)
        if not match:
            logger.warning("Could not find endpoint in 'foundry service status' output")
            logger.debug(f"Output was: {output}")
            return None

        base_endpoint = match.group(0)

        # Convert to chat completions endpoint
        # From: http://127.0.0.1:60779
        # To:   http://127.0.0.1:60779/v1/chat/completions
        chat_endpoint = f"{base_endpoint}/v1/chat/completions"

        logger.info(f"✓ Detected Foundry Local endpoint: {chat_endpoint}")

        # Cache for session
        _cached_endpoint = chat_endpoint
        return chat_endpoint

    except FileNotFoundError:
        logger.warning("'foundry' command not found - is AI Foundry CLI installed?")
        logger.info("Install with: brew install azure/ai-foundry/foundry")
        return None
    except subprocess.TimeoutExpired:
        logger.warning("'foundry service status' command timed out")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error detecting Foundry endpoint: {e}")
        logger.debug("Exception details:", exc_info=True)
        return None


def clear_endpoint_cache():
    """Clear the cached endpoint (useful for testing or after service restart)."""
    global _cached_endpoint
    _cached_endpoint = None
    logger.debug("Cleared Foundry endpoint cache")


def check_foundry_service_running() -> bool:
    """Check if Foundry Local service is running.

    Returns:
        True if service is running, False otherwise.
    """
    try:
        result = subprocess.run(
            ["foundry", "service", "status"],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Check if output contains "running"
        if result.returncode == 0 and "running" in result.stdout.lower():
            return True

        return False

    except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
        return False


def get_foundry_setup_instructions() -> str:
    """Get user-friendly setup instructions for Foundry Local.

    Returns:
        Formatted setup instructions string.
    """
    return """
To use local mode with AI Foundry:

1. Install AI Foundry CLI:
   brew install azure/ai-foundry/foundry

2. Download Phi-4 model:
   foundry model get phi-4

3. Start the service:
   foundry service start

4. Load the model:
   foundry model load phi-4

5. Verify it's running:
   foundry service status

Then restart this application - it will auto-detect the endpoint.

Alternatively, switch to remote mode: --mode remote
""".strip()
