"""Interactive CLI interface for screenshot organization chat."""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from agent_client import AgentClient
from session_manager import SessionManager
from utils.config import load_config, should_show_model_name
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


class CLIInterface:
    """Interactive command-line interface for screenshot organization."""

    def __init__(self, session_id: Optional[str] = None, mode: Optional[str] = None,
                 local_config: Optional[dict] = None):
        """Initialize CLI interface.

        Args:
            session_id: Optional session ID to resume. If None, creates new session.
            mode: Operation mode ("local", "remote", or None for auto-detect).
            local_config: Optional dict with local mode config (port, endpoint).
        """
        self.console = Console()
        self.agent_client = AgentClient(mode=mode, local_config=local_config)
        self.session_manager = SessionManager()
        self.session_id = session_id or self.session_manager.create_session()
        self.thread = None  # Will be initialized in chat_loop

        logger.info(f"CLI initialized with session: {self.session_id}")

    async def initialize_thread(self):
        """Initialize or load thread for conversation."""
        # Try to load previous session if resuming
        if self.session_id:
            thread_data = self.session_manager.load_session(self.session_id)
            if thread_data:
                try:
                    self.thread = await self.agent_client.deserialize_thread(thread_data)
                    logger.info(f"Resumed session {self.session_id} with saved thread")
                except Exception as e:
                    logger.warning(f"Failed to deserialize thread: {e}, creating new thread")
                    self.thread = self.agent_client.get_new_thread()
            else:
                self.thread = self.agent_client.get_new_thread()
        else:
            self.thread = self.agent_client.get_new_thread()

    def show_welcome(self):
        """Display welcome message and instructions."""
        # Mode-specific info
        mode = self.agent_client.mode
        model_name = self.agent_client.model_name

        mode_emoji = "🏠" if mode == "local" else "☁️"
        mode_desc = f"[bold {('green' if mode == 'local' else 'cyan')}]{mode_emoji} {mode.upper()} MODE[/bold {('green' if mode == 'local' else 'cyan')}] - {model_name}"

        if mode == "local":
            mode_info = "• TESTING MODE: Basic chat only (no tools)\n• Use for quick testing of conversation flow\n• Switch to remote mode for production use"
        else:
            mode_info = "• PRODUCTION MODE: Full AI agent capabilities\n• Screenshot analysis, file organization, tool support\n• Running on Azure OpenAI cloud infrastructure"

        welcome_text = f"""
[bold cyan]Screenshot Organizer AI Assistant[/bold cyan]

{mode_desc}
{mode_info}

Commands:
  • Just chat naturally - ask me to analyze or organize screenshots
  • [bold]/help[/bold] - Show this help message
  • [bold]/clear[/bold] - Clear conversation history
  • [bold]/quit[/bold] or [bold]/exit[/bold] - Exit the program

Examples:
  • "Analyze this screenshot: /path/to/screenshot.png"
  • "Organize all screenshots in ~/Desktop/screenshots"
  • "What categories do you support?"
        """
        self.console.print(Panel(welcome_text, border_style="cyan"))
        self.console.print()

    def show_help(self):
        """Display help message."""
        help_text = """
[bold]Available Commands:[/bold]

[bold cyan]/help[/bold cyan] - Show this help message
[bold cyan]/clear[/bold cyan] - Clear conversation history and start fresh
[bold cyan]/quit, /exit[/bold cyan] - Exit the program

[bold]Usage Tips:[/bold]

• Provide absolute paths to screenshots or folders
• The assistant will use OCR first for speed, vision model as fallback
• You can ask for confirmation before organizing large batches
• Original files can be archived (configured in config file)

[bold]Supported Categories:[/bold]
code, errors, documentation, design, communication, memes, other
        """
        self.console.print(Panel(help_text, title="Help", border_style="cyan"))
        self.console.print()

    async def handle_command(self, user_input: str) -> bool:
        """Handle special commands.

        Args:
            user_input: User's input string.

        Returns:
            True if input was a command (don't send to chat), False otherwise.
        """
        command = user_input.strip().lower()

        if command in ["/quit", "/exit"]:
            self.console.print("[cyan]Goodbye! 👋[/cyan]")
            return True

        if command == "/help":
            self.show_help()
            return True

        if command == "/clear":
            # Create new thread and clear session
            self.thread = self.agent_client.get_new_thread()
            self.session_manager.clear_session(self.session_id)
            self.console.print("[green]✓ Conversation history cleared[/green]\n")
            return True

        return False

    async def chat_loop(self):
        """Main interactive chat loop (async)."""
        # Complete async initialization (MCP client for remote mode)
        await self.agent_client.async_init()

        # Initialize thread
        await self.initialize_thread()

        self.show_welcome()

        # Trigger proactive introduction (remote mode only)
        if self.agent_client.mode == "remote":
            self.console.print()
            with self.console.status("[cyan]Agent initializing...[/cyan]", spinner="dots"):
                # Send simple trigger to start conversation
                intro_response = await self.agent_client.chat("Hello", thread=self.thread)

            # Display agent's introduction
            if should_show_model_name():
                mode_emoji = "☁️"
                mode_color = "cyan"
                model_name = self.agent_client.model_name
                self.console.print(f"[bold {mode_color}]Assistant {mode_emoji} {model_name}[/bold {mode_color}]\n")
            else:
                self.console.print(f"[bold cyan]Assistant[/bold cyan]\n")

            self.console.print(intro_response)
            self.console.print()

        try:
            while True:
                # Get user input
                try:
                    user_input = Prompt.ask("[bold green]You[/bold green]")
                except EOFError:
                    # Handle Ctrl+D
                    self.console.print("\n[cyan]Goodbye! 👋[/cyan]")
                    break

                # Skip empty input
                if not user_input.strip():
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    if await self.handle_command(user_input):
                        if user_input.strip().lower() in ["/quit", "/exit"]:
                            break
                        continue

                # Send to agent client
                self.console.print()
                with self.console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
                    response = await self.agent_client.chat(user_input, thread=self.thread)

                # Display response with model indicator
                if should_show_model_name():
                    mode_emoji = "🏠" if self.agent_client.mode == "local" else "☁️"
                    mode_color = "green" if self.agent_client.mode == "local" else "cyan"
                    model_badge = f"[{mode_color}]{mode_emoji} {self.agent_client.mode}[/{mode_color}]"
                    self.console.print(f"[bold blue]Assistant[/bold blue] {model_badge}")
                else:
                    self.console.print("[bold blue]Assistant[/bold blue]")
                self.agent_client.display_response(response)

                # Save session after each exchange
                thread_data = await self.agent_client.serialize_thread(self.thread)
                self.session_manager.save_session(self.session_id, thread_data)

        except KeyboardInterrupt:
            self.console.print("\n\n[cyan]Interrupted. Goodbye! 👋[/cyan]")
        except Exception as e:
            self.console.print(f"\n[red]Error: {e}[/red]")
            logger.error(f"Chat loop error: {e}", exc_info=True)
        finally:
            # Save final session state
            try:
                thread_data = await self.agent_client.serialize_thread(self.thread)
                self.session_manager.save_session(self.session_id, thread_data)
                logger.info("Session saved before exit")
            except Exception as e:
                logger.error(f"Failed to save session on exit: {e}")

            # Cleanup MCP client
            await self.agent_client.cleanup()


@click.command()
@click.option(
    "--session",
    help="Session ID to resume previous conversation"
)
@click.option(
    "--local",
    is_flag=True,
    help="Use local testing mode (Phi-4-mini, no tools). Default is remote mode (GPT-4, full capabilities)."
)
@click.option(
    "--port",
    type=int,
    help="Port for local Foundry service (e.g., 60779). Only for --local mode. Auto-detected if not specified."
)
@click.option(
    "--endpoint",
    help="Full endpoint URL for local Foundry service (overrides --port). Only for --local mode."
)
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Path to custom config file"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging"
)
def main(session: Optional[str], local: bool, port: Optional[int],
         endpoint: Optional[str], config: Optional[Path], debug: bool):
    """Interactive AI assistant for organizing screenshots.

    REMOTE MODE (default):
      • Full AI agent capabilities with GPT-4
      • Screenshot analysis, batch processing, file organization
      • Requires: Azure credentials (AZURE_AI_CHAT_ENDPOINT, AZURE_AI_CHAT_KEY, AZURE_AI_MODEL_DEPLOYMENT)
      • Get credentials from: https://ai.azure.com or Azure Portal

    LOCAL MODE (--local flag):
      • Testing/debugging only - uses Phi-4-mini, NO tools
      • Basic chat for testing conversation flow
      • NO screenshot analysis, NO file organization
      • Requires: Azure AI Foundry CLI running

    Examples:
      python -m src.cli_interface                        # Remote mode (default)
      python -m src.cli_interface --local                # Local testing mode
      python -m src.cli_interface --local --port 60779   # Local with explicit port
      python -m src.cli_interface --session abc123       # Resume previous session
    """
    # Setup logging
    log_level = "DEBUG" if debug else "INFO"
    setup_logging(level=log_level)

    # Load configuration
    if config:
        logger.info(f"Loading custom config from: {config}")
        # TODO: Support custom config file loading
    else:
        load_config()

    # Determine mode from --local flag
    import os

    mode = "local" if local else "remote"
    logger.info(f"Starting in {mode} mode")

    # Validate Azure credentials only for remote mode
    if mode == "remote":
        endpoint = os.environ.get("AZURE_AI_CHAT_ENDPOINT")
        if not endpoint:
            console = Console()
            console.print("[red]Error: Azure credentials not configured for remote mode.[/red]")
            console.print()
            console.print("Required environment variables:")
            console.print("  • AZURE_AI_CHAT_ENDPOINT - Your Azure endpoint")
            console.print("  • AZURE_AI_CHAT_KEY - Your API key (or use 'az login')")
            console.print("  • AZURE_AI_MODEL_DEPLOYMENT - Your model name (e.g., gpt-4o)")
            console.print()
            console.print("Supported endpoints:")
            console.print("  - AI Foundry: https://xxx.services.ai.azure.com/api/projects/xxx")
            console.print("  - Azure OpenAI: https://xxx.cognitiveservices.azure.com")
            console.print()
            console.print("Get credentials from: [cyan]https://ai.azure.com[/cyan] or Azure Portal")
            console.print("See .env.example for setup instructions")
            console.print()
            console.print("Tip: Use [bold]--mode local[/bold] for quick testing (basic chat only, no tools)")
            sys.exit(1)

    # Build endpoint configuration for local mode
    local_config = {}
    if port:
        local_config["port"] = port
    if endpoint:
        local_config["endpoint"] = endpoint

    # Create and run CLI
    try:
        cli = CLIInterface(session_id=session, mode=mode, local_config=local_config if local_config else None)
        asyncio.run(cli.chat_loop())
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        console = Console()
        console.print(f"[red]Fatal error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
