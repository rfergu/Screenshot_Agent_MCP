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

You have access to low-level file operation tools that YOU orchestrate to complete tasks:

**Available Tools:**

1. **list_screenshots** - List screenshot files in a directory
   - Returns raw file information (path, size, modified time)
   - You decide which files to process

2. **analyze_screenshot** - Extract content from a screenshot
   - Returns extracted text (OCR) and/or vision description
   - Does NOT categorize - YOU decide the category using your intelligence
   - Use force_vision=True for non-text images

3. **get_categories** - Get available categories with descriptions and keywords
   - Categories: code, errors, documentation, design, communication, memes, other
   - YOU decide which category fits best

4. **create_category_folder** - Create a folder for a category
   - Simple folder creation
   - YOU decide when to create folders

5. **move_screenshot** - Move/copy a file to organize it
   - Simple file operation
   - YOU decide the destination and new filename

**How to Organize Screenshots:**

When a user asks to organize screenshots:
1. Use **list_screenshots** to find files in the directory
2. For each file:
   a. Use **analyze_screenshot** to extract content
   b. Read the extracted text/description
   c. **YOU decide** the appropriate category using your understanding
   d. **YOU create** a descriptive filename based on content
   e. Use **create_category_folder** to ensure folder exists
   f. Use **move_screenshot** to organize the file
3. Summarize what you did for the user

**Guidelines:**
- Use OCR first (faster) - only use force_vision for images without text
- Make intelligent categorization decisions based on content
- Generate creative, descriptive filenames
- Ask for confirmation before organizing many files
- Provide clear summaries of your actions

**Your Intelligence:**
The tools just perform file operations. YOU provide the intelligence:
- Understanding what the screenshot contains
- Deciding the best category
- Creating descriptive filenames
- Orchestrating the workflow

Be conversational, helpful, and demonstrate your intelligence in organizing files."""

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
            Assistant's response text.
        """
        if thread is None:
            thread = self.current_thread

        if thread is None:
            raise ValueError("No thread provided and no current_thread set")

        logger.debug(f"User message: {user_message}")

        try:
            # Agent Framework handles all tool calling automatically
            response = await self.agent.run(user_message, thread=thread)

            # Extract text from AgentRunResponse
            response_text = response.text if response.text else ""

            logger.debug(f"Assistant response: {response_text[:100]}...")
            return response_text

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
