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

import os
from typing import Optional

from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import DefaultAzureCredential
from rich.console import Console
from rich.markdown import Markdown

from mcp_client_wrapper import MCPClientWrapper, get_agent_framework_tools
from utils.config import get as config_get, get_mode
from utils.logger import get_logger

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

    # Production system prompt - full capabilities with tool support
    REMOTE_SYSTEM_PROMPT = """You are an intelligent AI assistant that helps users organize their screenshots.

CRITICAL: When a user asks you to do something, IMMEDIATELY call the appropriate tools. DO NOT just describe what you will do - ACTUALLY DO IT by calling tools.

**Available Tools:**

1. **list_screenshots(directory, recursive, max_files)** - List screenshot files
2. **analyze_screenshot(file_path, force_vision)** - Extract text/description from screenshot
3. **get_categories()** - Get available categories
4. **create_category_folder(category, base_path)** - Create category folder
5. **move_screenshot(source_path, destination_folder, new_filename, archive_original)** - Move/rename file

**Your Role:**
- Tools return FACTS (text, file lists, etc.)
- YOU make DECISIONS (categories, filenames, workflow)
- YOU provide INTELLIGENCE (understanding content, creative naming)

**Action Protocol:**

When user asks to analyze a screenshot:
1. IMMEDIATELY call analyze_screenshot(file_path, force_vision=False)
2. Show the user what you found (extracted text or description)
3. Based on the content, decide the category
4. Suggest a descriptive filename
5. Offer to organize it

When user asks to organize screenshots:
1. IMMEDIATELY call list_screenshots(directory)
2. Show how many files found
3. For each file: call analyze_screenshot, decide category, create filename
4. Ask for confirmation if many files
5. Execute organization with create_category_folder and move_screenshot
6. Report results

**IMPORTANT RULES:**
- Call tools IMMEDIATELY when user requests action
- Show tool results to the user (don't hide what you found)
- Make intelligent decisions based on tool output
- Be concise - less narration, more action
- Don't say "I will do X" - just DO X by calling the tool

Example:
User: "Analyze /path/to/screenshot.png"
You: [CALL analyze_screenshot] → [SHOW RESULTS] → [DECIDE CATEGORY] → [SUGGEST FILENAME]

NOT:
You: "I'll analyze that screenshot for you. Let me use OCR..." [STOPS WITHOUT CALLING TOOL]

Execute tools immediately. Show results. Make decisions. Be helpful."""

    # Testing-only system prompt - basic chat, no tool support
    LOCAL_SYSTEM_PROMPT = """You are a helpful AI assistant for testing conversation flows.

IMPORTANT: You are running in LOCAL TESTING MODE. This means:
- You do NOT have access to screenshot analysis tools
- You do NOT have access to file organization capabilities
- You can only provide basic conversational responses

Your purpose in this mode is to help developers test:
- Agent conversation flow
- Instruction following
- Response quality and tone

When users ask about screenshots or file organization, politely explain that these features
require remote mode (GPT-4) for reliable operation. Local mode is for quick testing only.

Be conversational and helpful within these limitations."""

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
        self.mode = self._detect_mode(mode)

        # Initialize appropriate chat client based on mode
        if self.mode == "local":
            self._init_local_client(local_config=local_config)
        else:
            self._init_remote_client(endpoint, credential)

        # MCP client (will be started async in remote mode)
        self.mcp_client = None

        # Select system prompt and tools based on mode
        if self.mode == "local":
            # LOCAL: Testing mode - basic chat only, no tools
            system_prompt = self.LOCAL_SYSTEM_PROMPT
            tools = []  # No tools in local mode - not reliable
            logger.info("Using LOCAL system prompt (testing mode, no tools)")
        else:
            # REMOTE: Production mode - full capabilities with MCP tools
            # Tools will be initialized async (empty for now, set in async_init)
            system_prompt = self.REMOTE_SYSTEM_PROMPT
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

    def _detect_mode(self, explicit_mode: Optional[str] = None) -> str:
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

    def _init_local_client(self, local_config: Optional[dict] = None):
        """Initialize local AI Foundry chat client.

        Args:
            local_config: Optional dict with 'port' or 'endpoint' keys for explicit configuration.
        """
        try:
            from phi3_chat_client import LocalFoundryChatClient

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
            self.chat_client = LocalFoundryChatClient(endpoint=endpoint_config, model=model)
            self.model_name = f"{model} (local)"

            # Get the actual endpoint (after auto-detection)
            self.endpoint = self.chat_client.endpoint

            logger.info("🏠 LOCAL MODE: Using AI Foundry local inference")
            logger.info(f"   - Chat model: {model}")
            logger.info(f"   - Endpoint: {self.endpoint}")
            if self.chat_client.auto_detected:
                logger.info("   - Endpoint auto-detected via 'foundry service status'")
            elif local_config:
                logger.info("   - Endpoint from CLI arguments")
            logger.info("   - Mode: TESTING ONLY (basic chat, no tools)")
            logger.info("   - Use for: Quick testing of conversation flow")
            logger.info("   - Zero API costs")

        except ImportError as e:
            logger.error(f"Failed to import LocalFoundryChatClient: {e}")
            raise ImportError(
                "Local mode requires AI Foundry and azure-ai-inference.\n"
                "Install AI Foundry: https://aka.ms/ai-foundry/sdk\n"
                "Start server: foundry run phi-4-mini\n"
                "Note: Local mode is for testing only (basic chat, no tools)\n"
                "Or switch to remote mode for production: --mode remote"
            ) from e

    def _init_remote_client(self, endpoint: Optional[str] = None, credential: Optional[str] = None):
        """Initialize remote Azure OpenAI chat client."""
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
            "remote.deployment", "gpt-4"
        )
        self.model_name = self.model

        # Get credential
        api_key = credential or os.environ.get("AZURE_AI_CHAT_KEY")

        # Initialize Agent Framework chat client
        # AzureOpenAIChatClient works with both Foundry and Azure OpenAI endpoints
        if api_key:
            # Use API key authentication
            self.chat_client = AzureOpenAIChatClient(
                endpoint=self.endpoint,
                api_key=api_key,
                deployment_name=self.model
            )
            logger.info("☁️  REMOTE MODE: Using Azure OpenAI with API key")
        else:
            # Fall back to DefaultAzureCredential (az login)
            self.chat_client = AzureOpenAIChatClient(
                endpoint=self.endpoint,
                credential=DefaultAzureCredential(),
                deployment_name=self.model
            )
            logger.info("☁️  REMOTE MODE: Using Azure OpenAI with DefaultAzureCredential")

        logger.info(f"   - Endpoint: {self.endpoint}")
        logger.info(f"   - Model deployment: {self.model}")

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
            if self.agent.tools:
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
                            formatted_result = json.dumps(result_dict, indent=2)
                            # Truncate if too long
                            if len(formatted_result) > 800:
                                formatted_result = formatted_result[:800] + "\n... (truncated)"
                            response_parts.append(f"📊 **Tool Result:**\n```json\n{formatted_result}\n```")
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
