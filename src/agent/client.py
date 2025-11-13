"""Agent Framework client for screenshot organization with MCP Client Integration.

Architecture: Agent Framework WITH MCP Client (embedded)

Supports both:
- Local mode: TESTING ONLY - basic chat for conversation flow testing (no tools, no MCP)
- Remote mode: PRODUCTION - Agent Framework WITH embedded MCP client for all file operations

In remote mode, this demonstrates the unified architecture:
  Agent Framework (Brain)
    ↓ contains
  MCP Client Wrapper (embedded)
    ↓ calls via stdio
  MCP Server (subprocess)
    ↓ mediates
  File System (ALL access through MCP protocol)
"""

from typing import Optional

from agent_framework import ChatAgent
from rich.console import Console
from rich.markdown import Markdown

from screenshot_mcp.client_wrapper import MCPClientWrapper, get_agent_framework_tools
from utils.logger import get_logger

from .prompts import REMOTE_SYSTEM_PROMPT, LOCAL_SYSTEM_PROMPT
from .modes import detect_mode, init_local_client, init_remote_client

logger = get_logger(__name__)


class AgentClient:
    """Agent Framework client with embedded MCP Client for screenshot organization.

    Demonstrates: Agent Framework WITH MCP Client Integration

    Supports two operation modes:
    - Local: TESTING ONLY - basic chat for testing conversation flow (no tools, no MCP)
    - Remote: PRODUCTION - Agent Framework WITH embedded MCP client for all file operations

    Remote Mode Architecture:
    - AgentClient embeds MCPClientWrapper
    - MCP client manages MCP server subprocess (stdio transport)
    - All file system operations mediated through MCP protocol
    - Agent (GPT-4) makes intelligent decisions
    - MCP server provides low-level file operation tools

    Mode is determined by:
    1. Explicit mode parameter
    2. SCREENSHOT_ORGANIZER_MODE environment variable
    3. Config file demo.mode setting
    4. Default: "remote"
    """

    def __init__(self, mode: Optional[str] = None, endpoint: Optional[str] = None,
                 credential: Optional[str] = None, local_config: Optional[dict] = None):
        """Initialize agent client with local or remote AI.

        Args:
            mode: Operation mode ("local", "remote", or None for auto-detect).
            endpoint: Azure endpoint (remote mode only). If None, reads from env.
            credential: Azure API key (remote mode only). If None, reads from env.
            local_config: Optional dict with local mode config (port, endpoint).
        """
        # Determine operation mode
        self.mode = detect_mode(mode)

        # Initialize appropriate chat client based on mode
        if self.mode == "local":
            chat_client, model_name, endpoint_url, auto_detected = init_local_client(local_config=local_config)
            self.chat_client = chat_client
            self.model_name = model_name
            self.endpoint = endpoint_url
        else:
            chat_client, model_name, endpoint_url = init_remote_client(endpoint, credential)
            self.chat_client = chat_client
            self.model_name = model_name
            self.endpoint = endpoint_url

        # MCP client (will be started async in remote mode)
        self.mcp_client = None

        # Select system prompt and tools based on mode
        if self.mode == "local":
            # LOCAL: Testing mode - basic chat only, no tools
            system_prompt = LOCAL_SYSTEM_PROMPT
            tools = []  # No tools in local mode - not reliable
            logger.info("Using LOCAL system prompt (testing mode, no tools)")
        else:
            # REMOTE: Production mode - full capabilities with MCP tools
            # Tools will be initialized async (empty for now, set in async_init)
            system_prompt = REMOTE_SYSTEM_PROMPT
            tools = []  # Will be populated in async_init
            logger.info("Using REMOTE system prompt (production mode with MCP tools)")

        # Create agent with mode-specific configuration
        self.agent = ChatAgent(
            chat_client=self.chat_client,
            instructions=system_prompt,
            tools=tools
        )

        # Console for rich output
        self.console = Console()

        # Current thread (managed externally by CLI)
        self.current_thread = None

        logger.info(f"✓ AgentClient initialized in {self.mode.upper()} mode")
        logger.info(f"Model: {self.model_name}")

    async def async_init(self):
        """Complete async initialization (MCP client for remote mode).

        Must be called after __init__ for remote mode to enable tools.
        """
        if self.mode == "remote" and self.mcp_client is None:
            logger.info("Starting MCP client for tool access...")
            self.mcp_client = MCPClientWrapper()
            await self.mcp_client.start()

            # Get MCP tools and add to agent
            mcp_tools = get_agent_framework_tools(self.mcp_client)

            # Extract just the functions for Agent Framework
            tool_functions = [tool["function"] for tool in mcp_tools]

            # Update agent's tools
            self.agent.tools = tool_functions

            logger.info(f"✓ MCP client started, {len(tool_functions)} tools available")
            logger.info("✓ All file system operations will go through MCP protocol")

    async def cleanup(self):
        """Clean up resources (stop MCP client)."""
        if self.mcp_client:
            logger.info("Stopping MCP client...")
            await self.mcp_client.stop()
            self.mcp_client = None
            logger.info("✓ MCP client stopped")

    def get_new_thread(self):
        """Create a new conversation thread.

        Returns:
            AgentThread object for managing conversation state.
        """
        thread = self.agent.get_new_thread()
        self.current_thread = thread
        logger.info("Created new conversation thread")
        return thread

    async def chat(self, user_message: str, thread=None) -> str:
        """Send a message and get a response with automatic tool orchestration.

        Args:
            user_message: User's message.
            thread: Optional AgentThread to use. If None, uses current_thread.

        Returns:
            Assistant's response text (includes tool call details for transparency).
        """
        if thread is None:
            thread = self.current_thread

        if thread is None:
            raise ValueError("No thread provided and no current_thread set")

        logger.debug(f"User message: {user_message}")

        try:
            # Agent Framework handles all tool calling automatically
            # Pass tools explicitly to run() to ensure they're available
            if hasattr(self.agent, 'tools') and self.agent.tools:
                response = await self.agent.run(user_message, thread=thread, tools=self.agent.tools)
            else:
                response = await self.agent.run(user_message, thread=thread)

            logger.debug(f"Response type: {type(response)}")
            logger.debug(f"Response has text: {hasattr(response, 'text')}")

            # Build response with tool call transparency
            # Messages are in the RESPONSE, not the thread!
            response_parts = []

            if hasattr(response, 'messages') and response.messages:
                # Get messages from this turn's response
                new_messages = response.messages
                logger.debug(f"Processing {len(new_messages)} messages from response")

                for idx, msg in enumerate(new_messages):
                    logger.info(f"Message {idx}: role={getattr(msg, 'role', 'unknown')}, has_tool_calls={hasattr(msg, 'tool_calls')}")
                    if hasattr(msg, 'tool_calls'):
                        logger.info(f"  Tool calls count: {len(msg.tool_calls) if msg.tool_calls else 0}")
                    # Show tool calls
                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        for tool_call in msg.tool_calls:
                            tool_name = tool_call.function.name if hasattr(tool_call.function, 'name') else 'unknown'
                            # Try to get arguments for more detail
                            try:
                                import json
                                args = json.loads(tool_call.function.arguments) if hasattr(tool_call.function, 'arguments') else {}
                                args_str = json.dumps(args, indent=2)
                                response_parts.append(f"🔧 **Calling Tool:** `{tool_name}`\n```json\n{args_str}\n```")
                            except:
                                response_parts.append(f"🔧 **Calling Tool:** `{tool_name}`")
                            logger.info(f"Tool called: {tool_name}")

                    # Show tool results
                    if hasattr(msg, 'role') and msg.role == 'tool':
                        tool_result = msg.content if hasattr(msg, 'content') else 'No result'

                        # Try to parse and format JSON results
                        try:
                            import json
                            result_dict = json.loads(tool_result) if isinstance(tool_result, str) else tool_result

                            # Check if this is analyze_screenshot result with processing_method
                            processing_indicator = ""
                            if isinstance(result_dict, dict) and 'processing_method' in result_dict:
                                method = result_dict['processing_method']
                                if method == 'ocr':
                                    processing_indicator = "✅ **Local OCR processing completed**\n\n"
                                elif method == 'vision':
                                    processing_indicator = "🔍 **Cloud vision analysis completed**\n\n"

                            formatted_result = json.dumps(result_dict, indent=2)
                            # Truncate if too long
                            if len(formatted_result) > 800:
                                formatted_result = formatted_result[:800] + "\n... (truncated)"
                            response_parts.append(f"{processing_indicator}📊 **Tool Result:**\n```json\n{formatted_result}\n```")
                        except:
                            # Not JSON or formatting failed, show as-is
                            result_str = str(tool_result)
                            if len(result_str) > 800:
                                result_str = result_str[:800] + "... (truncated)"
                            response_parts.append(f"📊 **Tool Result:**\n```\n{result_str}\n```")

                        logger.info(f"Tool result received")

            # Add the final assistant response
            response_text = response.text if response.text else ""
            logger.info(f"Final response.text: '{response_text[:200] if response_text else '(empty)'}...'")

            if response_parts:
                # Combine tool calls + results + final response
                if response_text:
                    full_response = "\n\n".join(response_parts) + "\n\n**Analysis:**\n\n" + response_text
                else:
                    # Tool calls happened but no final response from GPT-4
                    full_response = "\n\n".join(response_parts) + "\n\n**Note:** Waiting for analysis from GPT-4..."
                    logger.warning("Tool calls executed but no final response text from GPT-4")
            else:
                # No tool calls detected
                if response_text:
                    full_response = response_text
                else:
                    full_response = "(No response generated)"
                    logger.warning("No tool calls and no response text")

            logger.info(f"Returning response with {len(response_parts)} tool interactions, text length: {len(response_text)}")
            return full_response

        except Exception as e:
            error_msg = f"Error communicating with Azure AI: {e}"
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

    async def serialize_thread(self, thread=None) -> dict:
        """Serialize thread state for persistence.

        Args:
            thread: Optional AgentThread to serialize. If None, uses current_thread.

        Returns:
            Serialized thread data as dictionary.
        """
        if thread is None:
            thread = self.current_thread

        if thread is None:
            return {}

        serialized = await thread.serialize()
        logger.debug("Thread serialized for persistence")
        return serialized

    async def deserialize_thread(self, serialized_data: dict):
        """Restore thread state from serialized data.

        Args:
            serialized_data: Serialized thread data from serialize_thread().

        Returns:
            Restored AgentThread object.
        """
        thread = await self.agent.deserialize_thread(serialized_data)
        self.current_thread = thread
        logger.info("Thread deserialized from persistence")
        return thread
