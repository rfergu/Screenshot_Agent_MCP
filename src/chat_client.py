"""Azure AI Foundry / Azure OpenAI orchestrated chat client for screenshot organization."""

import json
import os
from typing import Any, Dict, List, Optional, Union

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import (
    AssistantMessage,
    ChatCompletionsToolDefinition,
    CompletionsFinishReason,
    FunctionDefinition,
    SystemMessage,
    ToolMessage,
    UserMessage,
)
from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI
from rich.console import Console
from rich.markdown import Markdown

from mcp_tools import MCPToolHandlers
from utils.config import get as config_get
from utils.logger import get_logger

logger = get_logger(__name__)


class ChatClient:
    """Azure AI Foundry / Azure OpenAI chat interface with MCP tool integration.

    Supports both:
    - AI Foundry serverless endpoints: https://xxx.services.ai.azure.com/api/projects/xxx
    - Azure OpenAI resource endpoints: https://xxx.cognitiveservices.azure.com
    """

    SYSTEM_PROMPT = """You are a helpful AI assistant that helps users organize their screenshots.

You have access to three powerful tools for screenshot analysis and organization:

1. **analyze_screenshot** - Analyzes a single screenshot to determine its category and suggest a filename
   - Uses OCR for text-based screenshots (faster)
   - Falls back to vision model for images without sufficient text
   - Use force_vision=True only when specifically requested or when OCR clearly won't work

2. **batch_process** - Processes multiple screenshots in a folder
   - Can process folders recursively
   - Optionally organizes files automatically after analysis
   - Provides detailed statistics

3. **organize_file** - Moves and renames a screenshot to the appropriate category folder
   - Categories: code, errors, documentation, design, communication, memes, other
   - Optionally archives original files

Guidelines:
- Always try OCR first for efficiency (it's much faster than vision)
- When users ask to "organize" or "sort", use batch_process with organize=True
- Provide clear, helpful summaries of what was done
- Ask for confirmation before organizing large numbers of files
- Suggest descriptive filenames based on content

Be conversational, helpful, and efficient. Focus on making screenshot organization easy for the user."""

    def __init__(self, endpoint: Optional[str] = None, credential: Optional[str] = None):
        """Initialize chat client with Azure AI Foundry or Azure OpenAI.

        Args:
            endpoint: Azure endpoint. If None, reads from AZURE_AI_CHAT_ENDPOINT env var.
                     Supports both AI Foundry and Azure OpenAI formats.
            credential: Azure API key. If None, reads from AZURE_AI_CHAT_KEY env var.
        """
        # Get endpoint
        self.endpoint = endpoint or os.environ.get("AZURE_AI_CHAT_ENDPOINT")
        if not self.endpoint:
            raise ValueError(
                "Azure endpoint not provided. Set AZURE_AI_CHAT_ENDPOINT environment variable "
                "or pass endpoint parameter.\n"
                "Supported formats:\n"
                "  - AI Foundry: https://xxx.services.ai.azure.com/api/projects/xxx\n"
                "  - Azure OpenAI: https://xxx.cognitiveservices.azure.com"
            )

        # Get model deployment name
        self.model = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT") or config_get(
            "api.azure_model_deployment", "gpt-4"
        )
        self.max_context_length = config_get("api.max_context_length", 8000)

        # Detect endpoint type and initialize appropriate client
        if "cognitiveservices.azure.com" in self.endpoint:
            self.endpoint_type = "azure_openai"
            self._init_azure_openai(credential)
        elif "services.ai.azure.com" in self.endpoint:
            self.endpoint_type = "ai_foundry"
            self._init_ai_foundry(credential)
        else:
            raise ValueError(
                f"Unknown endpoint format: {self.endpoint}\n"
                "Expected either:\n"
                "  - AI Foundry: https://xxx.services.ai.azure.com/api/projects/xxx\n"
                "  - Azure OpenAI: https://xxx.cognitiveservices.azure.com"
            )

        self.console = Console()
        self.conversation_history: List[Any] = []
        self.tool_handlers = MCPToolHandlers()

        logger.info(f"ChatClient initialized with model deployment: {self.model}")
        logger.info(f"Endpoint: {self.endpoint}")
        logger.info(f"Endpoint type: {self.endpoint_type}")

    def _init_azure_openai(self, credential: Optional[str]):
        """Initialize Azure OpenAI client.

        Args:
            credential: API key for authentication.
        """
        api_key = credential or os.environ.get("AZURE_AI_CHAT_KEY")
        if not api_key:
            raise ValueError(
                "Azure OpenAI requires API key. Set AZURE_AI_CHAT_KEY environment variable."
            )

        # Azure OpenAI endpoint should not include /chat/completions path
        # The SDK adds this automatically
        api_base = self.endpoint.split("/chat")[0] if "/chat" in self.endpoint else self.endpoint

        self.client = AzureOpenAI(
            api_key=api_key,
            api_version="2024-08-01-preview",
            azure_endpoint=api_base
        )
        logger.info("Initialized Azure OpenAI client")

    def _init_ai_foundry(self, credential: Optional[str]):
        """Initialize Azure AI Foundry client.

        Args:
            credential: API key for authentication (optional, can use Azure CLI).
        """
        api_key = credential or os.environ.get("AZURE_AI_CHAT_KEY")
        if api_key:
            self.credential = AzureKeyCredential(api_key)
            logger.info("Using Azure API key authentication")
        else:
            # Fall back to DefaultAzureCredential (az login)
            self.credential = DefaultAzureCredential()
            logger.info("Using DefaultAzureCredential (Azure CLI authentication)")

        self.client = ChatCompletionsClient(
            endpoint=self.endpoint,
            credential=self.credential
        )
        logger.info("Initialized AI Foundry client")

    def _get_tool_definitions(self) -> List[ChatCompletionsToolDefinition]:
        """Get Azure AI tool definitions for MCP tools.

        Returns:
            List of tool definitions in Azure AI format.
        """
        return [
            ChatCompletionsToolDefinition(
                function=FunctionDefinition(
                    name="analyze_screenshot",
                    description="Analyze a screenshot using OCR or vision model to determine its category and suggest a filename",
                    parameters={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Absolute path to the screenshot file"
                            },
                            "force_vision": {
                                "type": "boolean",
                                "description": "Force use of vision model even if OCR would be sufficient",
                            }
                        },
                        "required": ["path"]
                    }
                )
            ),
            ChatCompletionsToolDefinition(
                function=FunctionDefinition(
                    name="batch_process",
                    description="Process all screenshots in a folder, analyzing and categorizing each one",
                    parameters={
                        "type": "object",
                        "properties": {
                            "folder": {
                                "type": "string",
                                "description": "Path to the folder containing screenshots"
                            },
                            "recursive": {
                                "type": "boolean",
                                "description": "Process subfolders recursively",
                            },
                            "max_files": {
                                "type": "integer",
                                "description": "Maximum number of files to process (1-1000)"
                            },
                            "organize": {
                                "type": "boolean",
                                "description": "Automatically organize files after analysis",
                            }
                        },
                        "required": ["folder"]
                    }
                )
            ),
            ChatCompletionsToolDefinition(
                function=FunctionDefinition(
                    name="organize_file",
                    description="Move and rename a screenshot file based on its category",
                    parameters={
                        "type": "object",
                        "properties": {
                            "source_path": {
                                "type": "string",
                                "description": "Current path of the file to organize"
                            },
                            "category": {
                                "type": "string",
                                "enum": ["code", "errors", "documentation", "design",
                                       "communication", "memes", "other"],
                                "description": "Category for organization"
                            },
                            "new_filename": {
                                "type": "string",
                                "description": "New filename for the file (without extension)"
                            },
                            "archive_original": {
                                "type": "boolean",
                                "description": "Keep a copy of the original file in archive",
                            },
                            "base_path": {
                                "type": "string",
                                "description": "Base path for organized files"
                            }
                        },
                        "required": ["source_path", "category", "new_filename"]
                    }
                )
            )
        ]

    def _get_tool_definitions_openai(self) -> List[Dict[str, Any]]:
        """Get OpenAI-format tool definitions for MCP tools.

        Returns:
            List of tool definitions in OpenAI format.
        """
        return [
            {
                "type": "function",
                "function": {
                    "name": "analyze_screenshot",
                    "description": "Analyze a screenshot using OCR or vision model to determine its category and suggest a filename",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Absolute path to the screenshot file"
                            },
                            "force_vision": {
                                "type": "boolean",
                                "description": "Force use of vision model even if OCR would be sufficient",
                            }
                        },
                        "required": ["path"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "batch_process",
                    "description": "Process all screenshots in a folder, analyzing and categorizing each one",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "folder": {
                                "type": "string",
                                "description": "Path to the folder containing screenshots"
                            },
                            "recursive": {
                                "type": "boolean",
                                "description": "Process subfolders recursively",
                            },
                            "max_files": {
                                "type": "integer",
                                "description": "Maximum number of files to process (1-1000)"
                            },
                            "organize": {
                                "type": "boolean",
                                "description": "Automatically organize files after analysis",
                            }
                        },
                        "required": ["folder"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "organize_file",
                    "description": "Move and rename a screenshot file based on its category",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source_path": {
                                "type": "string",
                                "description": "Current path of the file to organize"
                            },
                            "category": {
                                "type": "string",
                                "enum": ["code", "errors", "documentation", "design",
                                       "communication", "memes", "other"],
                                "description": "Category for organization"
                            },
                            "new_filename": {
                                "type": "string",
                                "description": "New filename for the file (without extension)"
                            },
                            "archive_original": {
                                "type": "boolean",
                                "description": "Keep a copy of the original file in archive",
                            },
                            "base_path": {
                                "type": "string",
                                "description": "Base path for organized files"
                            }
                        },
                        "required": ["source_path", "category", "new_filename"]
                    }
                }
            }
        ]

    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call through the MCP handlers.

        Args:
            tool_name: Name of the tool to execute.
            arguments: Tool arguments.

        Returns:
            Tool execution result.
        """
        logger.info(f"Executing tool: {tool_name} with args: {arguments}")

        try:
            if tool_name == "analyze_screenshot":
                return self.tool_handlers.analyze_screenshot(**arguments)
            elif tool_name == "batch_process":
                return self.tool_handlers.batch_process(**arguments)
            elif tool_name == "organize_file":
                return self.tool_handlers.organize_file(**arguments)
            else:
                raise ValueError(f"Unknown tool: {tool_name}")
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {"error": str(e)}

    def chat(self, user_message: str) -> str:
        """Send a message and get a response with tool calling support.

        Args:
            user_message: User's message.

        Returns:
            Assistant's response text.
        """
        logger.debug(f"User message: {user_message}")

        # Route to appropriate client implementation
        if self.endpoint_type == "azure_openai":
            return self._chat_azure_openai(user_message)
        else:
            return self._chat_ai_foundry(user_message)

    def _chat_ai_foundry(self, user_message: str) -> str:
        """Chat implementation for Azure AI Foundry endpoint.

        Args:
            user_message: User's message.

        Returns:
            Assistant's response text.
        """
        # Add user message to history
        self.conversation_history.append(UserMessage(content=user_message))

        # Prepare messages for API call
        messages = [SystemMessage(content=self.SYSTEM_PROMPT)] + self.conversation_history

        try:
            # Initial API call with tools
            response = self.client.complete(
                model=self.model,
                messages=messages,
                tools=self._get_tool_definitions(),
            )

            assistant_message = response.choices[0].message

            # Handle tool calls
            while response.choices[0].finish_reason == CompletionsFinishReason.TOOL_CALLS:
                logger.debug(f"Assistant requested {len(assistant_message.tool_calls)} tool calls")

                # Add assistant message with tool calls to history
                self.conversation_history.append(
                    AssistantMessage(tool_calls=assistant_message.tool_calls)
                )

                # Execute each tool call
                if assistant_message.tool_calls:
                    for tool_call in assistant_message.tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments.replace("'", '"'))

                        # Execute tool
                        tool_result = self._execute_tool(tool_name, tool_args)

                        # Add tool result to history
                        self.conversation_history.append(
                            ToolMessage(
                                content=json.dumps(tool_result),
                                tool_call_id=tool_call.id
                            )
                        )

                # Get next response with tool results
                messages = [SystemMessage(content=self.SYSTEM_PROMPT)] + self.conversation_history

                response = self.client.complete(
                    model=self.model,
                    messages=messages,
                    tools=self._get_tool_definitions(),
                )

                assistant_message = response.choices[0].message

            # Final response without tool calls
            response_text = assistant_message.content or ""

            # Add final response to history
            self.conversation_history.append(AssistantMessage(content=response_text))

            logger.debug(f"Assistant response: {response_text[:100]}...")
            return response_text

        except Exception as e:
            error_msg = f"Error communicating with Azure AI Foundry: {e}"
            logger.error(error_msg, exc_info=True)
            return f"Sorry, I encountered an error: {str(e)}"

    def _chat_azure_openai(self, user_message: str) -> str:
        """Chat implementation for Azure OpenAI endpoint.

        Args:
            user_message: User's message.

        Returns:
            Assistant's response text.
        """
        # Convert AI Foundry message objects to OpenAI dict format
        def convert_messages_to_openai(messages):
            """Convert Azure AI Foundry messages to OpenAI format."""
            openai_messages = []
            for msg in messages:
                if isinstance(msg, SystemMessage):
                    openai_messages.append({"role": "system", "content": msg.content})
                elif isinstance(msg, UserMessage):
                    openai_messages.append({"role": "user", "content": msg.content})
                elif isinstance(msg, AssistantMessage):
                    msg_dict = {"role": "assistant"}
                    if hasattr(msg, "content") and msg.content:
                        msg_dict["content"] = msg.content
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        msg_dict["tool_calls"] = [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments
                                }
                            }
                            for tc in msg.tool_calls
                        ]
                    openai_messages.append(msg_dict)
                elif isinstance(msg, ToolMessage):
                    openai_messages.append({
                        "role": "tool",
                        "content": msg.content,
                        "tool_call_id": msg.tool_call_id
                    })
            return openai_messages

        # Add user message to history
        self.conversation_history.append(UserMessage(content=user_message))

        try:
            # Prepare messages for API call
            messages = [SystemMessage(content=self.SYSTEM_PROMPT)] + self.conversation_history
            openai_messages = convert_messages_to_openai(messages)

            # Initial API call with tools
            response = self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                tools=self._get_tool_definitions_openai(),
            )

            choice = response.choices[0]
            assistant_message = choice.message

            # Handle tool calls
            while choice.finish_reason == "tool_calls":
                logger.debug(f"Assistant requested {len(assistant_message.tool_calls)} tool calls")

                # Convert OpenAI tool calls to AI Foundry format for storage
                from azure.ai.inference.models import ChatCompletionsToolCall, FunctionCall

                tool_calls_foundry = [
                    ChatCompletionsToolCall(
                        id=tc.id,
                        function=FunctionCall(
                            name=tc.function.name,
                            arguments=tc.function.arguments
                        )
                    )
                    for tc in assistant_message.tool_calls
                ]

                # Add assistant message with tool calls to history
                self.conversation_history.append(
                    AssistantMessage(tool_calls=tool_calls_foundry)
                )

                # Execute each tool call
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    # Execute tool
                    tool_result = self._execute_tool(tool_name, tool_args)

                    # Add tool result to history
                    self.conversation_history.append(
                        ToolMessage(
                            content=json.dumps(tool_result),
                            tool_call_id=tool_call.id
                        )
                    )

                # Get next response with tool results
                messages = [SystemMessage(content=self.SYSTEM_PROMPT)] + self.conversation_history
                openai_messages = convert_messages_to_openai(messages)

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=openai_messages,
                    tools=self._get_tool_definitions_openai(),
                )

                choice = response.choices[0]
                assistant_message = choice.message

            # Final response without tool calls
            response_text = assistant_message.content or ""

            # Add final response to history
            self.conversation_history.append(AssistantMessage(content=response_text))

            logger.debug(f"Assistant response: {response_text[:100]}...")
            return response_text

        except Exception as e:
            error_msg = f"Error communicating with Azure OpenAI: {e}"
            logger.error(error_msg, exc_info=True)
            return f"Sorry, I encountered an error: {str(e)}"

    def display_response(self, response: str):
        """Display assistant response with rich formatting.

        Args:
            response: Response text to display.
        """
        self.console.print()
        self.console.print(Markdown(response))
        self.console.print()

    def reset_conversation(self):
        """Clear conversation history to start fresh."""
        self.conversation_history = []
        logger.info("Conversation history cleared")

    def get_conversation_length(self) -> int:
        """Get approximate token count of conversation history.

        Returns:
            Approximate token count.
        """
        # Rough estimate: 4 characters per token
        total_chars = sum(
            len(str(getattr(msg, "content", "")))
            for msg in self.conversation_history
        )
        return total_chars // 4

    def should_truncate_context(self) -> bool:
        """Check if conversation context should be truncated.

        Returns:
            True if context is too long.
        """
        return self.get_conversation_length() > self.max_context_length

    def truncate_context(self, keep_recent: int = 10):
        """Truncate conversation history to keep only recent messages.

        Args:
            keep_recent: Number of recent message pairs to keep.
        """
        if len(self.conversation_history) > keep_recent * 2:
            # Keep only the last N exchanges
            self.conversation_history = self.conversation_history[-(keep_recent * 2):]
            logger.info(f"Truncated conversation history to {len(self.conversation_history)} messages")

    def serialize_conversation_history(self) -> List[Dict[str, Any]]:
        """Convert conversation history to JSON-serializable format.

        Returns:
            List of message dictionaries that can be JSON serialized.
        """
        serialized = []
        for msg in self.conversation_history:
            msg_dict = {"type": type(msg).__name__}

            if isinstance(msg, SystemMessage):
                msg_dict["content"] = msg.content
            elif isinstance(msg, UserMessage):
                msg_dict["content"] = msg.content
            elif isinstance(msg, AssistantMessage):
                if hasattr(msg, "content") and msg.content:
                    msg_dict["content"] = msg.content
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    msg_dict["tool_calls"] = [
                        {
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in msg.tool_calls
                    ]
            elif isinstance(msg, ToolMessage):
                msg_dict["content"] = msg.content
                msg_dict["tool_call_id"] = msg.tool_call_id

            serialized.append(msg_dict)

        return serialized

    def deserialize_conversation_history(self, serialized: List[Dict[str, Any]]):
        """Restore conversation history from JSON-serializable format.

        Args:
            serialized: List of message dictionaries from JSON.
        """
        from azure.ai.inference.models import ChatCompletionsToolCall, FunctionCall

        self.conversation_history = []
        for msg_dict in serialized:
            msg_type = msg_dict.get("type")

            if msg_type == "SystemMessage":
                self.conversation_history.append(SystemMessage(content=msg_dict["content"]))
            elif msg_type == "UserMessage":
                self.conversation_history.append(UserMessage(content=msg_dict["content"]))
            elif msg_type == "AssistantMessage":
                content = msg_dict.get("content")
                tool_calls_data = msg_dict.get("tool_calls")

                if tool_calls_data:
                    # Reconstruct tool calls
                    tool_calls = [
                        ChatCompletionsToolCall(
                            id=tc["id"],
                            function=FunctionCall(
                                name=tc["function"]["name"],
                                arguments=tc["function"]["arguments"]
                            )
                        )
                        for tc in tool_calls_data
                    ]
                    self.conversation_history.append(AssistantMessage(tool_calls=tool_calls))
                else:
                    self.conversation_history.append(AssistantMessage(content=content))
            elif msg_type == "ToolMessage":
                self.conversation_history.append(
                    ToolMessage(
                        content=msg_dict["content"],
                        tool_call_id=msg_dict["tool_call_id"]
                    )
                )

        logger.info(f"Deserialized {len(self.conversation_history)} messages")
