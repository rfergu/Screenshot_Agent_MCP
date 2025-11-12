"""Agent Framework client for screenshot organization with Azure AI orchestration."""

import os
from typing import Optional

from agent_framework import ChatAgent
from agent_framework.azure import AzureOpenAIChatClient
from azure.identity import DefaultAzureCredential
from rich.console import Console
from rich.markdown import Markdown

from mcp_tools import analyze_screenshot, batch_process, organize_file
from utils.config import get as config_get
from utils.logger import get_logger

logger = get_logger(__name__)


class AgentClient:
    """Azure AI Agent client with integrated screenshot organization tools.

    Uses Microsoft Agent Framework to orchestrate conversations with Azure AI
    models (Foundry or Azure OpenAI) and provide screenshot analysis tools.
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
        """Initialize agent client with Azure AI.

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
            logger.info("Using Azure API key authentication")
        else:
            # Fall back to DefaultAzureCredential (az login)
            self.chat_client = AzureOpenAIChatClient(
                endpoint=self.endpoint,
                credential=DefaultAzureCredential(),
                deployment_name=self.model
            )
            logger.info("Using DefaultAzureCredential (Azure CLI authentication)")

        # Create agent with screenshot organization tools
        self.agent = ChatAgent(
            chat_client=self.chat_client,
            instructions=self.SYSTEM_PROMPT,
            tools=[analyze_screenshot, batch_process, organize_file]
        )

        # Console for rich output
        self.console = Console()

        # Current thread (managed externally by CLI)
        self.current_thread = None

        logger.info(f"AgentClient initialized with model deployment: {self.model}")
        logger.info(f"Endpoint: {self.endpoint}")

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

            logger.debug(f"Assistant response: {response[:100]}...")
            return response

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
