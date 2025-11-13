"""Mode-specific client initialization logic.

Provides functions for initializing local (testing) and remote (production) chat clients.
"""

import os
from typing import Optional
from azure.identity import DefaultAzureCredential
from agent_framework.azure import AzureOpenAIChatClient

from utils.config import get as config_get, get_mode
from utils.logger import get_logger

logger = get_logger(__name__)


def detect_mode(explicit_mode: Optional[str] = None) -> str:
    """Detect operation mode from explicit parameter, env, or config.

    Args:
        explicit_mode: Explicitly specified mode.

    Returns:
        Mode string: "local" or "remote"
    """
    # Priority 1: Explicit parameter
    if explicit_mode and explicit_mode.lower() in ["local", "remote"]:
        logger.debug(f"Mode set explicitly: {explicit_mode}")
        return explicit_mode.lower()

    # Priority 2: Config/environment (get_mode checks both)
    detected_mode = get_mode()
    logger.debug(f"Mode detected from config/env: {detected_mode}")

    # "auto" mode is not yet implemented - default to remote for now
    if detected_mode == "auto":
        logger.warning("Auto mode not yet implemented, defaulting to remote")
        return "remote"

    return detected_mode


def init_local_client(local_config: Optional[dict] = None):
    """Initialize local AI Foundry chat client.

    Args:
        local_config: Optional dict with 'port' or 'endpoint' keys for explicit configuration.

    Returns:
        Tuple of (chat_client, model_name, endpoint, auto_detected_flag)
    """
    try:
        from local_foundry_chat_client import LocalFoundryChatClient

        # Determine endpoint with priority:
        # 1. Explicit endpoint from CLI (highest priority)
        # 2. Port from CLI (build endpoint)
        # 3. Config file setting
        # 4. Auto-detect (default)
        endpoint_config = "auto"

        if local_config:
            if "endpoint" in local_config:
                # Explicit endpoint override
                endpoint_config = local_config["endpoint"]
                logger.info(f"Using CLI endpoint: {endpoint_config}")
            elif "port" in local_config:
                # Build endpoint from port (/v1 base, SDK appends /chat/completions)
                port = local_config["port"]
                endpoint_config = f"http://127.0.0.1:{port}/v1"
                logger.info(f"Using CLI port {port}: {endpoint_config}")

        # Fall back to config file if no CLI override
        if endpoint_config == "auto":
            endpoint_config = config_get("local.endpoint", "auto")

        model = config_get("local.model", "phi-4")

        # Initialize AI Foundry local client
        chat_client = LocalFoundryChatClient(endpoint=endpoint_config, model=model)
        model_name = f"{model} (local)"

        # Get the actual endpoint (after auto-detection)
        endpoint = chat_client.endpoint
        auto_detected = chat_client.auto_detected

        logger.info("🏠 LOCAL MODE: Using AI Foundry local inference")
        logger.info(f"   - Chat model: {model}")
        logger.info(f"   - Endpoint: {endpoint}")
        if auto_detected:
            logger.info("   - Endpoint auto-detected via 'foundry service status'")
        elif local_config:
            logger.info("   - Endpoint from CLI arguments")
        logger.info("   - Mode: TESTING ONLY (basic chat, no tools)")
        logger.info("   - Use for: Quick testing of conversation flow")
        logger.info("   - Zero API costs")

        return chat_client, model_name, endpoint, auto_detected

    except ImportError as e:
        logger.error(f"Failed to import LocalFoundryChatClient: {e}")
        raise ImportError(
            "Local mode requires AI Foundry and azure-ai-inference.\n"
            "Install AI Foundry: https://aka.ms/ai-foundry/sdk\n"
            "Start server: foundry run phi-4-mini\n"
            "Note: Local mode is for testing only (basic chat, no tools)\n"
            "Or switch to remote mode for production: --mode remote"
        ) from e


def init_remote_client(endpoint: Optional[str] = None, credential: Optional[str] = None):
    """Initialize remote Azure OpenAI chat client.

    Args:
        endpoint: Azure endpoint URL. If None, reads from AZURE_AI_CHAT_ENDPOINT env var.
        credential: Azure API key. If None, reads from AZURE_AI_CHAT_KEY env var or uses DefaultAzureCredential.

    Returns:
        Tuple of (chat_client, model_name, endpoint)
    """
    # Get endpoint
    endpoint_url = endpoint or os.environ.get("AZURE_AI_CHAT_ENDPOINT")
    if not endpoint_url:
        raise ValueError(
            "Azure endpoint not provided. Set AZURE_AI_CHAT_ENDPOINT environment variable "
            "or pass endpoint parameter.\n"
            "Supported formats:\n"
            "  - AI Foundry: https://xxx.services.ai.azure.com/api/projects/xxx\n"
            "  - Azure OpenAI: https://xxx.cognitiveservices.azure.com"
        )

    # Get model deployment name
    model = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT") or config_get(
        "remote.deployment", "gpt-4"
    )
    model_name = model

    # Get credential
    api_key = credential or os.environ.get("AZURE_AI_CHAT_KEY")

    # Initialize Agent Framework chat client
    # AzureOpenAIChatClient works with both Foundry and Azure OpenAI endpoints
    if api_key:
        # Use API key authentication
        chat_client = AzureOpenAIChatClient(
            endpoint=endpoint_url,
            api_key=api_key,
            deployment_name=model
        )
        logger.info("☁️  REMOTE MODE: Using Azure OpenAI with API key")
    else:
        # Fall back to DefaultAzureCredential (az login)
        chat_client = AzureOpenAIChatClient(
            endpoint=endpoint_url,
            credential=DefaultAzureCredential(),
            deployment_name=model
        )
        logger.info("☁️  REMOTE MODE: Using Azure OpenAI with DefaultAzureCredential")

    logger.info(f"   - Endpoint: {endpoint_url}")
    logger.info(f"   - Model deployment: {model}")

    return chat_client, model_name, endpoint_url
