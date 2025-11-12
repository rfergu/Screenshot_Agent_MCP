"""Local Phi-3 chat client for Microsoft Agent Framework.

This module wraps the phi-3-vision-mlx model to work with Microsoft Agent
Framework, enabling fully local operation with no cloud dependencies.
"""

import json
from typing import Any, Dict, List, Optional, Union

from agent_framework._types import ChatMessage, ChatResponse
from utils.logger import get_logger

logger = get_logger(__name__)


class Phi3LocalChatClient:
    """Local Phi-3 chat client compatible with Microsoft Agent Framework.

    Provides a local alternative to Azure OpenAI by wrapping phi-3-vision-mlx
    to implement the Agent Framework ChatClient interface. Enables:
    - Fully local operation (no cloud calls)
    - Zero cost per query
    - Complete privacy (no data leaves device)
    - Same tool integration as Azure clients

    Note: This is a simplified implementation focused on chat completion.
    Full tool calling support is basic compared to GPT-4.
    """

    def __init__(self, model_path: Optional[str] = None, **kwargs):
        """Initialize local Phi-3 chat client.

        Args:
            model_path: Optional path to model files. If None, uses default.
            **kwargs: Additional configuration options (for compatibility).
        """
        self.model = None
        self.model_path = model_path
        self.model_name = "phi-3-vision-mlx"

        logger.info("🏠 Phi3LocalChatClient initialized (model will load on first use)")
        logger.info("Mode: FULLY LOCAL - no cloud dependencies")

    def _ensure_model_loaded(self):
        """Lazy load Phi-3 model on first use.

        Defers the expensive model loading (~8GB) until actually needed.
        """
        if self.model is None:
            logger.info("Loading Phi-3 Vision model for chat (this may take a moment)...")
            try:
                from phi3v import Phi3Vision
                self.model = Phi3Vision(self.model_path) if self.model_path else Phi3Vision()
                logger.info("✓ Phi-3 Vision model loaded successfully")
            except ImportError as e:
                logger.error(f"Failed to import phi-3-vision-mlx: {e}")
                raise ImportError(
                    "phi-3-vision-mlx not available for local mode. "
                    "Install with: pip install phi-3-vision-mlx\n"
                    "Or switch to remote mode: --mode remote"
                ) from e
            except Exception as e:
                logger.error(f"Failed to load Phi-3 Vision model: {e}")
                raise

    def _convert_messages_to_prompt(self, messages: Union[str, ChatMessage, List[Union[str, ChatMessage]]]) -> str:
        """Convert Agent Framework message format to Phi-3 prompt.

        Args:
            messages: Messages in Agent Framework format (str, ChatMessage, or list).

        Returns:
            Formatted prompt string for Phi-3.
        """
        # Normalize messages to list
        if isinstance(messages, str):
            msg_list = [{"role": "user", "content": messages}]
        elif isinstance(messages, ChatMessage):
            msg_list = [{"role": messages.role, "content": messages.content}]
        elif isinstance(messages, list):
            msg_list = []
            for msg in messages:
                if isinstance(msg, str):
                    msg_list.append({"role": "user", "content": msg})
                elif isinstance(msg, ChatMessage):
                    msg_list.append({"role": msg.role, "content": msg.content})
                elif isinstance(msg, dict):
                    msg_list.append(msg)
        else:
            msg_list = []

        prompt_parts = []

        for msg in msg_list:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if role == "system":
                prompt_parts.append(f"<|system|>\n{content}<|end|>")
            elif role == "user":
                prompt_parts.append(f"<|user|>\n{content}<|end|>")
            elif role == "assistant":
                prompt_parts.append(f"<|assistant|>\n{content}<|end|>")
            elif role == "tool":
                # Handle tool results
                tool_result = content
                prompt_parts.append(f"<|user|>\nTool result: {tool_result}<|end|>")

        # Add final assistant prompt
        prompt_parts.append("<|assistant|>")

        return "\n".join(prompt_parts)

    def _parse_tool_calls(self, response: str) -> Optional[List[Dict[str, Any]]]:
        """Attempt to parse tool calls from Phi-3 response.

        Phi-3 doesn't natively support function calling like GPT-4, but we can
        detect simple patterns like "I need to call analyze_screenshot with..."

        Args:
            response: The model's text response.

        Returns:
            List of tool call dictionaries if detected, None otherwise.
        """
        # Simple heuristic: look for tool mentions
        # This is basic - in production you'd want more sophisticated parsing
        tool_keywords = {
            "analyze_screenshot": ["analyze", "screenshot", "image"],
            "batch_process": ["batch", "process", "folder"],
            "organize_file": ["organize", "move", "file"]
        }

        # For now, return None - let Agent Framework handle this
        # In a full implementation, you'd parse the response for tool calls
        return None

    async def get_response(
        self,
        messages: Union[str, ChatMessage, List[Union[str, ChatMessage]]],
        *,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        tools: Optional[Any] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate chat response using local Phi-3 model.

        This implements the Agent Framework ChatClient interface for local operation.

        Args:
            messages: User messages in Agent Framework format (str, ChatMessage, or list).
            temperature: Sampling temperature (0.0-1.0), defaults to 0.7.
            max_tokens: Maximum tokens to generate, defaults to 2048.
            tools: Optional list of available tools (for function calling).
            **kwargs: Additional generation parameters.

        Returns:
            ChatResponse object from Agent Framework.
        """
        self._ensure_model_loaded()

        # Set defaults
        if temperature is None:
            temperature = 0.7
        if max_tokens is None:
            max_tokens = 2048

        # Convert messages to Phi-3 prompt format
        prompt = self._convert_messages_to_prompt(messages)

        logger.debug(f"🏠 LOCAL: Generating response with Phi-3 (max_tokens={max_tokens})")

        try:
            # Generate response using Phi-3
            response_text = self.model.generate(prompt)

            if not response_text:
                response_text = "I apologize, but I couldn't generate a response. Could you rephrase your question?"

            logger.debug(f"🏠 LOCAL: Generated {len(response_text)} characters")

            # Return ChatResponse object
            return ChatResponse(content=response_text)

        except Exception as e:
            logger.error(f"Error generating local response: {e}", exc_info=True)
            # Return error response
            error_msg = f"I encountered an error processing your request locally: {str(e)}\n\nTip: You can try remote mode with --mode remote"
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
