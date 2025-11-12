"""Local AI Foundry chat client for Microsoft Agent Framework.

This module uses AI Foundry's local inference server (Phi-4) to work with
Microsoft Agent Framework, enabling fully local operation with no cloud dependencies.

Requires:
- AI Foundry CLI installed (foundry)
- Phi-4 model downloaded (foundry cache list)
- Inference server running (foundry run phi-4)
"""

import json
from typing import Any, Dict, List, Optional, Union

from agent_framework._types import ChatMessage, ChatResponse
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage, AssistantMessage
from utils.logger import get_logger
from utils.foundry_local import detect_foundry_endpoint, detect_model_id, get_foundry_setup_instructions, clear_endpoint_cache

logger = get_logger(__name__)


class LocalFoundryChatClient:
    """Local AI Foundry chat client compatible with Microsoft Agent Framework.

    Uses AI Foundry's local inference server with Phi-4 model. Provides:
    - Fully local operation (no cloud calls)
    - Zero cost per query
    - Complete privacy (no data leaves device)
    - Same tool integration as Azure clients

    Note: Requires AI Foundry inference server running locally.
    Start with: foundry run phi-4
    """

    def __init__(self,
                 endpoint: Optional[str] = "auto",
                 model: str = "phi-4",
                 **kwargs):
        """Initialize local AI Foundry chat client.

        Args:
            endpoint: Local inference server endpoint. Options:
                - "auto" (default): Auto-detect via 'foundry service status'
                - Specific URL: e.g., "http://127.0.0.1:60779/v1/chat/completions"
                - None: Same as "auto"
            model: Model name to use (default: phi-4)
            **kwargs: Additional configuration options (for compatibility).
        """
        self.model_name = model
        self.endpoint = None
        self.auto_detected = False

        # Endpoint resolution with fallback chain:
        # 1. Auto-detect via 'foundry service status' (if endpoint is "auto" or None)
        # 2. Use provided endpoint (if specific URL given)
        # 3. Fall back to default port with warning
        if endpoint is None or endpoint == "auto":
            logger.debug("Attempting to auto-detect Foundry Local endpoint...")
            detected_endpoint = detect_foundry_endpoint()

            if detected_endpoint:
                self.endpoint = detected_endpoint
                self.auto_detected = True
                logger.info(f"✓ Auto-detected Foundry endpoint: {self.endpoint}")
            else:
                # Fallback to default
                self.endpoint = "http://127.0.0.1:5272/v1/chat/completions"
                logger.warning("⚠️  Could not auto-detect Foundry endpoint, using default port 5272")
                logger.warning("    This may not work if service is on a different port")
                logger.info("    Run 'foundry service status' to see actual endpoint")
        else:
            # Use provided endpoint
            self.endpoint = endpoint
            logger.info(f"Using configured endpoint: {self.endpoint}")

        # Detect the actual model ID from /v1/models endpoint
        # Foundry Local uses IDs like "Phi-4-generic-gpu:1" not "phi-4"
        base_endpoint = self.endpoint.replace("/v1/chat/completions", "")
        detected_model_id = detect_model_id(model, base_endpoint)

        if detected_model_id:
            self.model_name = detected_model_id
            logger.info(f"✓ Using model ID: {self.model_name}")
        else:
            # Keep the simple name as fallback, but warn
            self.model_name = model
            logger.warning(f"⚠️  Could not detect full model ID, using: {self.model_name}")
            logger.warning("    This may cause 404 errors. Check 'foundry model load phi-4'")

        # Initialize Azure AI Inference client (works with local server too)
        self.client = ChatCompletionsClient(
            endpoint=self.endpoint,
            credential={}  # Local doesn't need credentials
        )

        logger.info(f"🏠 LocalFoundryChatClient initialized")
        logger.info(f"   Endpoint: {self.endpoint}")
        logger.info(f"   Model: {self.model_name}")
        logger.info("   Mode: FULLY LOCAL - no cloud dependencies")

    def _reinitialize_connection(self):
        """Reinitialize endpoint and model detection (called on connection errors).

        This clears the cache and re-detects the endpoint/model, useful when the
        Foundry service restarts on a different port.
        """
        logger.info("Reinitializing connection (clearing cache and re-detecting)")
        clear_endpoint_cache()

        # Re-detect endpoint
        detected_endpoint = detect_foundry_endpoint()
        if detected_endpoint:
            self.endpoint = detected_endpoint
            logger.info(f"✓ Re-detected endpoint: {self.endpoint}")

            # Re-detect model ID
            base_endpoint = self.endpoint.replace("/v1/chat/completions", "")
            detected_model_id = detect_model_id(self.model_name.split("-")[0].lower() if "-" in self.model_name else self.model_name, base_endpoint)

            if detected_model_id:
                self.model_name = detected_model_id
                logger.info(f"✓ Re-detected model ID: {self.model_name}")

            # Reinitialize client with new endpoint
            self.client = ChatCompletionsClient(
                endpoint=self.endpoint,
                credential={}
            )
            return True
        else:
            logger.warning("Failed to re-detect endpoint")
            return False

    def _check_server_connection(self):
        """Check if AI Foundry inference server is running.

        Returns:
            bool: True if server is accessible, False otherwise.
        """
        try:
            # Quick test with minimal request
            test_response = self.client.complete(
                messages=[UserMessage(content="test")],
                model=self.model_name,
                max_tokens=1
            )
            return True
        except Exception as e:
            logger.warning(f"AI Foundry server not accessible: {e}")
            return False

    def _convert_to_inference_messages(
        self,
        messages: Union[str, ChatMessage, List[Union[str, ChatMessage]]]
    ) -> List:
        """Convert Agent Framework messages to Azure AI Inference format.

        Args:
            messages: Messages in Agent Framework format.

        Returns:
            List of SystemMessage, UserMessage, AssistantMessage objects.
        """
        # Normalize to list
        if isinstance(messages, str):
            return [UserMessage(content=messages)]
        elif isinstance(messages, ChatMessage):
            role = str(messages.role).lower()  # Convert Role enum to string
            content = messages.text or ""  # ChatMessage uses 'text' not 'content'
            if role == "system":
                return [SystemMessage(content=content)]
            elif role == "user":
                return [UserMessage(content=content)]
            elif role == "assistant":
                return [AssistantMessage(content=content)]
            else:
                return [UserMessage(content=content)]
        elif isinstance(messages, list):
            result = []
            for msg in messages:
                if isinstance(msg, str):
                    result.append(UserMessage(content=msg))
                elif isinstance(msg, ChatMessage):
                    role = str(msg.role).lower()  # Convert Role enum to string
                    content = msg.text or ""  # ChatMessage uses 'text' not 'content'
                    if role == "system":
                        result.append(SystemMessage(content=content))
                    elif role == "user":
                        result.append(UserMessage(content=content))
                    elif role == "assistant":
                        result.append(AssistantMessage(content=content))
                    else:
                        result.append(UserMessage(content=content))
                elif isinstance(msg, dict):
                    role = msg.get("role", "user").lower()
                    content = msg.get("content", "") or msg.get("text", "")  # Support both
                    if role == "system":
                        result.append(SystemMessage(content=content))
                    elif role == "user":
                        result.append(UserMessage(content=content))
                    elif role == "assistant":
                        result.append(AssistantMessage(content=content))
                    else:
                        result.append(UserMessage(content=content))
            return result
        else:
            return [UserMessage(content=str(messages))]

    async def get_response(
        self,
        messages: Union[str, ChatMessage, List[Union[str, ChatMessage]]],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[Any] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate chat response using local AI Foundry Phi-4 model.

        This implements the Agent Framework ChatClient interface for local operation.

        Args:
            messages: User messages in Agent Framework format (str, ChatMessage, or list).
            temperature: Sampling temperature (0.0-1.0), defaults to 0.7.
            max_tokens: Maximum tokens to generate, defaults to 1024.
            tools: Optional list of available tools (for function calling).
            **kwargs: Additional generation parameters.

        Returns:
            ChatResponse object from Agent Framework.
        """
        # Set defaults
        if temperature is None:
            temperature = 0.7
        if max_tokens is None:
            max_tokens = 1024

        # Convert messages to Azure AI Inference format
        inference_messages = self._convert_to_inference_messages(messages)

        logger.debug(f"🏠 LOCAL: Generating response with {self.model_name} (max_tokens={max_tokens})")

        # Retry logic: try once, and if connection error, re-detect and retry
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:
                # Call local AI Foundry server
                response = self.client.complete(
                    messages=inference_messages,
                    model=self.model_name,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

                # Extract response text
                response_text = response.choices[0].message.content

                if not response_text:
                    response_text = "I apologize, but I couldn't generate a response. Could you rephrase your question?"

                logger.debug(f"🏠 LOCAL: Generated {len(response_text)} characters")

                # Return ChatResponse object
                return ChatResponse(text=response_text)

            except Exception as e:
                error_type = type(e).__name__
                is_connection_error = "connection" in str(e).lower() or "not found" in str(e).lower()

                if attempt < max_attempts and is_connection_error:
                    # Retry: Re-detect endpoint/model and try again
                    logger.warning(f"Connection error on attempt {attempt}: {error_type}")
                    logger.info("Retrying with re-detected endpoint...")

                    if self._reinitialize_connection():
                        continue  # Retry with new endpoint
                    else:
                        # Re-detection failed, fall through to error handling
                        pass

                # Final attempt failed or non-connection error
                logger.error(f"Error generating local response (attempt {attempt}): {e}", exc_info=True)
                # Return error response with helpful message
                error_msg = (
                    f"I encountered an error connecting to the local AI Foundry server:\n"
                    f"{str(e)}\n\n"
                    f"{get_foundry_setup_instructions()}"
                )
                return ChatResponse(text=error_msg)

    # Additional methods for compatibility with Agent Framework

    async def get_model_info(self) -> Dict[str, Any]:
        """Get information about the local model.

        Returns:
            Model information dictionary.
        """
        return {
            "model": self.model_name,
            "provider": "local",
            "location": "on-device",
            "cost_per_token": 0.0,
            "privacy": "complete - no data leaves device"
        }
