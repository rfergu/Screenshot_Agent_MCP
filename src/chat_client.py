"""GPT-4 orchestrated chat client for screenshot organization."""

import json
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI
from rich.console import Console
from rich.markdown import Markdown

from mcp_tools import MCPToolHandlers
from utils.config import get as config_get
from utils.logger import get_logger

logger = get_logger(__name__)


class ChatClient:
    """GPT-4 orchestrated chat interface with MCP tool integration."""

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

    def __init__(self, api_key: Optional[str] = None):
        """Initialize chat client with OpenAI API.

        Args:
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided and OPENAI_API_KEY env var not set")

        self.client = OpenAI(api_key=self.api_key)
        self.model = config_get("api.openai_model", "gpt-4-turbo-preview")
        self.max_context_length = config_get("api.max_context_length", 8000)
        
        self.console = Console()
        self.conversation_history: List[Dict[str, Any]] = []
        self.tool_handlers = MCPToolHandlers()

        logger.info(f"ChatClient initialized with model: {self.model}")

    def _get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get OpenAI function definitions for MCP tools.

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
                                "default": False
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
                                "default": False
                            },
                            "max_files": {
                                "type": "integer",
                                "description": "Maximum number of files to process (1-1000)"
                            },
                            "organize": {
                                "type": "boolean",
                                "description": "Automatically organize files after analysis",
                                "default": False
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
                                "default": False
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
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        logger.debug(f"User message: {user_message}")

        # Prepare messages for API call
        messages = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ] + self.conversation_history

        try:
            # Initial API call with tools
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self._get_tool_definitions(),
                tool_choice="auto"
            )

            assistant_message = response.choices[0].message

            # Handle tool calls
            while assistant_message.tool_calls:
                logger.debug(f"Assistant requested {len(assistant_message.tool_calls)} tool calls")

                # Add assistant message with tool calls to history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        }
                        for tc in assistant_message.tool_calls
                    ]
                })

                # Execute each tool call
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    # Execute tool
                    tool_result = self._execute_tool(tool_name, tool_args)

                    # Add tool result to history
                    self.conversation_history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result)
                    })

                # Get next response from GPT-4 with tool results
                messages = [
                    {"role": "system", "content": self.SYSTEM_PROMPT}
                ] + self.conversation_history

                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self._get_tool_definitions(),
                    tool_choice="auto"
                )

                assistant_message = response.choices[0].message

            # Final response without tool calls
            response_text = assistant_message.content or ""

            # Add final response to history
            self.conversation_history.append({
                "role": "assistant",
                "content": response_text
            })

            logger.debug(f"Assistant response: {response_text[:100]}...")
            return response_text

        except Exception as e:
            error_msg = f"Error communicating with OpenAI: {e}"
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
            len(str(msg.get("content", "")))
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
