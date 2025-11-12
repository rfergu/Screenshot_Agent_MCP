"""Agent Framework client for screenshot organization with local or remote AI.

Supports both:
- Local mode: Fully on-device with Phi-3 Vision MLX (zero cost, complete privacy)
- Remote mode: Azure OpenAI cloud-powered (more capable, requires API)
"""

import os
from typing import Optional

from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import DefaultAzureCredential
from rich.console import Console
from rich.markdown import Markdown

from mcp_tools import analyze_screenshot, batch_process, organize_file
from utils.config import get as config_get, get_mode
from utils.logger import get_logger

logger = get_logger(__name__)


class AgentClient:
    """Agent Framework client with integrated screenshot organization tools.

    Supports two operation modes:
    - Local: Uses Phi-3 Vision MLX (fully on-device, zero cost, complete privacy)
    - Remote: Uses Azure OpenAI (cloud-powered, more capable)

    Mode is determined by:
    1. Explicit mode parameter
    2. SCREENSHOT_ORGANIZER_MODE environment variable
    3. Config file demo.mode setting
    4. Default: "remote"
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

    def __init__(self, mode: Optional[str] = None, endpoint: Optional[str] = None, credential: Optional[str] = None):
        """Initialize agent client with local or remote AI.

        Args:
            mode: Operation mode ("local", "remote", or None for auto-detect).
            endpoint: Azure endpoint (remote mode only). If None, reads from env.
            credential: Azure API key (remote mode only). If None, reads from env.
        """
        # Determine operation mode
        self.mode = self._detect_mode(mode)

        # Initialize appropriate chat client based on mode
        if self.mode == "local":
            self._init_local_client()
        else:
            self._init_remote_client(endpoint, credential)

        # Create agent with screenshot organization tools (same for both modes)
        self.agent = ChatAgent(
            chat_client=self.chat_client,
            instructions=self.SYSTEM_PROMPT,
            tools=[analyze_screenshot, batch_process, organize_file]
        )

        # Console for rich output
        self.console = Console()

        # Current thread (managed externally by CLI)
        self.current_thread = None

        logger.info(f"✓ AgentClient initialized in {self.mode.upper()} mode")
        logger.info(f"Model: {self.model_name}")

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

    def _init_local_client(self):
        """Initialize local AI Foundry chat client."""
        try:
            from phi3_chat_client import LocalFoundryChatClient

            # Get local endpoint configuration
            endpoint = config_get("local.endpoint", "http://127.0.0.1:5272/v1/chat/completions")
            model = config_get("local.model", "phi-4")

            # Initialize AI Foundry local client
            self.chat_client = LocalFoundryChatClient(endpoint=endpoint, model=model)
            self.model_name = f"{model} (local)"
            self.endpoint = endpoint

            logger.info("🏠 LOCAL MODE: Using AI Foundry local inference")
            logger.info(f"   - Chat model: {model}")
            logger.info(f"   - Vision model: phi-3-vision-mlx (for screenshots)")
            logger.info("   - Zero cost per query")
            logger.info("   - Complete privacy (no data leaves device)")
            logger.info("   - Requires: foundry run phi-4")

        except ImportError as e:
            logger.error(f"Failed to import LocalFoundryChatClient: {e}")
            raise ImportError(
                "Local mode requires AI Foundry and azure-ai-inference.\n"
                "Install AI Foundry: https://aka.ms/ai-foundry/sdk\n"
                "Start server: foundry run phi-4\n"
                "Or switch to remote mode: --mode remote"
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
