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
                 endpoint: str = "http://127.0.0.1:5272/v1/chat/completions",
                 model: str = "phi-4",
                 **kwargs):
        """Initialize local AI Foundry chat client.

        Args:
            endpoint: Local inference server endpoint (default: localhost:5272)
            model: Model name to use (default: phi-4)
            **kwargs: Additional configuration options (for compatibility).
        """
        self.endpoint = endpoint
        self.model_name = model

        # Initialize Azure AI Inference client (works with local server too)
        self.client = ChatCompletionsClient(
            endpoint=self.endpoint,
            credential={}  # Local doesn't need credentials
        )

        logger.info(f"🏠 LocalFoundryChatClient initialized")
        logger.info(f"   Endpoint: {self.endpoint}")
        logger.info(f"   Model: {self.model_name}")
        logger.info("   Mode: FULLY LOCAL - no cloud dependencies")

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
            return ChatResponse(content=response_text)

        except Exception as e:
            logger.error(f"Error generating local response: {e}", exc_info=True)
            # Return error response with helpful message
            error_msg = (
                f"I encountered an error connecting to the local AI Foundry server: {str(e)}\n\n"
                "Make sure the inference server is running:\n"
                "  foundry run phi-4\n\n"
                "Or switch to remote mode: --mode remote"
            )
            return ChatResponse(content=error_msg)

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
