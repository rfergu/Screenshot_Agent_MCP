"""Local AI Foundry chat client for Microsoft Agent Framework.

This module uses AI Foundry's local inference server (Phi-4) to work with
Microsoft Agent Framework, enabling fully local operation with no cloud dependencies.

Requires:
- AI Foundry CLI installed (foundry)
- Phi-4 model downloaded (foundry cache list)
- Inference server running (foundry run phi-4)
"""

import json
import re
from typing import Any, Dict, List, Optional, Union

from agent_framework import BaseChatClient, use_function_invocation
from agent_framework._types import ChatMessage, ChatResponse
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage, AssistantMessage
from utils.logger import get_logger
from utils.foundry_local import detect_foundry_endpoint, detect_model_id, get_foundry_setup_instructions, clear_endpoint_cache

logger = get_logger(__name__)


@use_function_invocation
class LocalFoundryChatClient(BaseChatClient):
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
                 model: str = "phi-4-mini",
                 **kwargs):
        """Initialize local AI Foundry chat client.

        Args:
            endpoint: Local inference server base URL (with /v1). Options:
                - "auto" (default): Auto-detect via 'foundry service status'
                - Specific base URL: e.g., "http://127.0.0.1:60779/v1"
                - None: Same as "auto"
              Note: SDK appends /chat/completions → http://127.0.0.1:PORT/v1/chat/completions
            model: Model name to use (default: phi-4-mini for tool calling support)
            **kwargs: Additional configuration options (for compatibility).
        """
        # Initialize parent BaseChatClient
        super().__init__(**kwargs)

        self.model_name = model
        self.endpoint = None
        self.auto_detected = False

        # Endpoint resolution with fallback chain:
        # 1. Auto-detect via 'foundry service status' (if endpoint is "auto" or None)
        # 2. Use provided endpoint (if specific URL given)
        # 3. Fall back to default port with warning
        if endpoint is None or endpoint == "auto":
            # Clear cache to get fresh endpoint/model detection
            clear_endpoint_cache()
            logger.debug("Attempting to auto-detect Foundry Local endpoint...")
            detected_endpoint = detect_foundry_endpoint()

            if detected_endpoint:
                self.endpoint = detected_endpoint
                self.auto_detected = True
                logger.info(f"✓ Auto-detected Foundry endpoint: {self.endpoint}")
            else:
                # Fallback to default (/v1 base, SDK appends /chat/completions)
                self.endpoint = "http://127.0.0.1:5272/v1"
                logger.warning("⚠️  Could not auto-detect Foundry endpoint, using default port 5272")
                logger.warning("    This may not work if service is on a different port")
                logger.info("    Run 'foundry service status' to see actual port")
        else:
            # Use provided endpoint
            self.endpoint = endpoint
            logger.info(f"Using configured endpoint: {self.endpoint}")

        # Detect the actual model ID from /v1/models endpoint
        # Foundry Local uses IDs like "Phi-4-generic-gpu:1" not "phi-4"
        # Endpoint is already the base URL (SDK appends /chat/completions)
        detected_model_id = detect_model_id(model, self.endpoint)

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

            # Re-detect model ID (endpoint is already base URL)
            detected_model_id = detect_model_id(self.model_name.split("-")[0].lower() if "-" in self.model_name else self.model_name, self.endpoint)

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

    def _parse_functools_format(self, text: str) -> List[Dict[str, Any]]:
        """Parse phi-4-mini's functools format into function call dictionaries.

        Phi-4-mini outputs function calls in a custom format:
        functools[{"name": "function_name", "arguments": {"arg": "value"}}, ...]

        This method extracts and parses these into a list of function call dicts.

        Args:
            text: Response text that may contain functools format

        Returns:
            List of dicts with 'name' and 'arguments' keys
        """
        function_calls = []

        # Pattern to match functools[...] format
        functools_pattern = r'functools\[(.*?)\]'
        matches = re.findall(functools_pattern, text, re.DOTALL)

        for match in matches:
            try:
                # Try to parse as JSON array first
                parsed = json.loads(f'[{match}]')
                if isinstance(parsed, list):
                    for call in parsed:
                        if isinstance(call, dict) and 'name' in call:
                            function_calls.append(call)
                logger.info(f"🏠 LOCAL: Parsed {len(function_calls)} function calls from functools format")
            except json.JSONDecodeError:
                # Fallback: try to parse individual function call format
                # e.g., get_weather(city="San Francisco")
                logger.debug(f"🏠 LOCAL: JSON parse failed, trying pattern match: {match}")

                # Pattern: function_name(arg1="value1", arg2="value2")
                call_pattern = r'(\w+)\((.*?)\)'
                call_matches = re.findall(call_pattern, match)

                for func_name, args_str in call_matches:
                    # Parse arguments
                    arguments = {}
                    # Pattern: arg="value" or arg='value'
                    arg_pattern = r'(\w+)=(["\'])(.*?)\2'
                    arg_matches = re.findall(arg_pattern, args_str)

                    for arg_name, _, arg_value in arg_matches:
                        arguments[arg_name] = arg_value

                    function_calls.append({
                        'name': func_name,
                        'arguments': arguments
                    })
                    logger.info(f"🏠 LOCAL: Parsed function call via pattern: {func_name}({arguments})")

        return function_calls

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

    async def _inner_get_response(
        self,
        *,
        messages: Union[str, ChatMessage, List[Union[str, ChatMessage]]],
        chat_options: Optional[Any] = None,
        **kwargs
    ) -> ChatResponse:
        """Generate chat response using local AI Foundry Phi-4 model.

        This implements the Agent Framework BaseChatClient interface for local operation.

        Args:
            messages: User messages in Agent Framework format (str, ChatMessage, or list).
            chat_options: Optional chat options object with configuration.
            **kwargs: Additional generation parameters (temperature, max_tokens, tools, etc.).

        Returns:
            ChatResponse object from Agent Framework.
        """
        # Extract parameters from kwargs and chat_options
        temperature = kwargs.get('temperature', getattr(chat_options, 'temperature', 0.7) if chat_options else 0.7)
        max_tokens = kwargs.get('max_tokens', getattr(chat_options, 'max_tokens', 1024) if chat_options else 1024)

        # Get tools from chat_options and convert to Azure AI Inference format
        tools = getattr(chat_options, 'tools', None) if chat_options else None

        # Convert AIFunction objects to Azure AI Inference tool format
        inference_tools = None
        if tools:
            from azure.ai.inference.models import ChatCompletionsToolDefinition, FunctionDefinition
            inference_tools = []
            for tool in tools:
                # Convert AIFunction to ChatCompletionsToolDefinition
                # Get the JSON schema from the AIFunction's input_model
                schema = tool.input_model.model_json_schema() if hasattr(tool, 'input_model') and tool.input_model else {}

                # Debug: log the schema to see parameter names
                if logger.isEnabledFor(10):  # DEBUG
                    logger.debug(f"🏠 LOCAL: Tool '{tool.name}' schema: {json.dumps(schema, indent=2)[:500]}")

                function_def = FunctionDefinition(
                    name=tool.name,
                    description=tool.description or "",
                    parameters=schema
                )
                tool_def = ChatCompletionsToolDefinition(function=function_def)
                inference_tools.append(tool_def)

            logger.debug(f"🏠 LOCAL: Converted {len(inference_tools)} AIFunction tools to Azure AI Inference format")

        # Convert messages to Azure AI Inference format
        inference_messages = self._convert_to_inference_messages(messages)

        # Inject functools instructions for phi-4-mini (Foundry Local workaround)
        # Phi-4-mini needs explicit instructions to use functools format since
        # Foundry Local doesn't properly support OpenAI-style function calling
        if inference_tools and len(inference_messages) > 0:
            # Find or create system message
            system_msg_idx = None
            for idx, msg in enumerate(inference_messages):
                if isinstance(msg, SystemMessage):
                    system_msg_idx = idx
                    break

            functools_instructions = """
FUNCTION CALLING: When you need to call a function, output ONLY the function call in this format:
functools[{"name": "function_name", "arguments": {"arg1": "value1"}}]

CRITICAL RULES:
1. Extract parameters from user's message (paths, values, etc.)
2. Use exact argument names from the function schema
3. Output the functools call ONCE - do not repeat it
4. After calling a function, WAIT for the result before responding
5. Do NOT add notes, explanations, or commentary around the function call
6. When you receive function results, provide a helpful natural language summary

Example - User: "Analyze screenshot: /path/file.png"
Good: functools[{"name": "analyze_screenshot", "arguments": {"path": "/path/file.png", "force_vision": false}}]
Bad: (Note: ...) functools[...] (Note: ...) functools[...]
"""

            if system_msg_idx is not None:
                # Append to existing system message
                existing_content = inference_messages[system_msg_idx].content
                inference_messages[system_msg_idx] = SystemMessage(
                    content=existing_content + "\n" + functools_instructions
                )
            else:
                # Prepend new system message
                inference_messages.insert(0, SystemMessage(content=functools_instructions))

            logger.debug(f"🏠 LOCAL: Added functools instructions to system message")

        logger.debug(f"🏠 LOCAL: Generating response with {self.model_name} (max_tokens={max_tokens})")
        if inference_tools:
            logger.info(f"🏠 LOCAL: Tool calling enabled with {len(inference_tools)} tools")

        # Retry logic: try once, and if connection error, re-detect and retry
        max_attempts = 2
        for attempt in range(1, max_attempts + 1):
            try:

                # Call local AI Foundry server
                # Note: tools parameter enables function calling if model supports it
                response = self.client.complete(
                    messages=inference_messages,
                    model=self.model_name,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    tools=inference_tools  # Pass converted tools for function calling
                )

                # Check response
                message = response.choices[0].message
                response_text = message.content or ""

                # Check for OpenAI-style tool_calls (preferred)
                has_openai_tool_calls = hasattr(message, 'tool_calls') and message.tool_calls is not None and len(message.tool_calls) > 0

                # Check for phi-4-mini's functools format (workaround for Foundry Local)
                functools_calls = []
                if response_text and 'functools[' in response_text:
                    functools_calls = self._parse_functools_format(response_text)

                has_functools_calls = len(functools_calls) > 0

                logger.info(f"🏠 LOCAL: Response - text: {bool(response_text)}, openai_tools: {has_openai_tool_calls}, functools: {has_functools_calls}")

                # Convert to Agent Framework ChatMessage format
                from agent_framework._types import ChatMessage as AFChatMessage, Role, FunctionCallContent

                # Build contents list
                contents = []
                clean_text = None

                # Add text content if present (remove functools format from display text)
                if response_text:
                    # Remove functools[...] from the text for cleaner display
                    # Use DOTALL flag to match across newlines
                    clean_text = re.sub(r'functools\[.*?\]', '', response_text, flags=re.DOTALL).strip()

                    # Also remove common artifacts and notes
                    clean_text = re.sub(r'\(Note:.*?\)', '', clean_text, flags=re.DOTALL).strip()

                    # Remove extra whitespace and newlines
                    clean_text = re.sub(r'\n\s*\n', '\n\n', clean_text).strip()

                    if clean_text:
                        contents.append({"type": "text", "text": clean_text})

                # Add OpenAI-style tool calls if present
                if has_openai_tool_calls:
                    for tool_call in message.tool_calls:
                        function_call_content = FunctionCallContent(
                            call_id=tool_call.id,
                            name=tool_call.function.name,
                            arguments=tool_call.function.arguments
                        )
                        contents.append(function_call_content)
                        logger.debug(f"  - OpenAI tool call: {tool_call.function.name}")

                # Add functools-format tool calls (Foundry Local workaround)
                elif has_functools_calls:
                    import uuid
                    for idx, func_call in enumerate(functools_calls):
                        # Generate a unique call_id
                        call_id = f"call_{uuid.uuid4().hex[:8]}"

                        # Convert arguments dict to JSON string (Agent Framework expects string)
                        arguments_json = json.dumps(func_call.get('arguments', {}))

                        function_call_content = FunctionCallContent(
                            call_id=call_id,
                            name=func_call['name'],
                            arguments=arguments_json
                        )
                        contents.append(function_call_content)
                        logger.info(f"  - functools call: {func_call['name']}({arguments_json})")

                # Create ChatMessage with contents
                # Use cleaned text for the text property (what gets displayed)
                display_text = clean_text if response_text else None

                chat_message = AFChatMessage(
                    role=Role.ASSISTANT,
                    contents=contents if contents else None,
                    text=display_text  # Use cleaned text without functools
                )

                logger.debug(f"🏠 LOCAL: Generated response with {len(contents)} content items")

                # Return ChatResponse object with the message
                return ChatResponse(messages=[chat_message])

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

    async def _inner_get_streaming_response(
        self,
        *,
        messages: Union[str, ChatMessage, List[Union[str, ChatMessage]]],
        chat_options: Optional[Any] = None,
        **kwargs
    ):
        """Streaming response not yet implemented for local mode.

        This is a placeholder to satisfy the BaseChatClient abstract method requirement.
        Streaming can be implemented in the future if needed.
        """
        raise NotImplementedError("Streaming responses are not yet supported in local mode")

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
