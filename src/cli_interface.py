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

    def __init__(self, session_id: Optional[str] = None, mode: Optional[str] = None):
        """Initialize CLI interface.

        Args:
            session_id: Optional session ID to resume. If None, creates new session.
            mode: Operation mode ("local", "remote", or None for auto-detect).
        """
        self.console = Console()
        self.agent_client = AgentClient(mode=mode)
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
            mode_info = "• Running fully on-device with Phi-3 Vision MLX\n• Zero cost, complete privacy, no data leaves your device"
        else:
            mode_info = "• Running on Azure OpenAI cloud infrastructure\n• More capable models, requires API access"

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
        # Initialize thread
        await self.initialize_thread()

        self.show_welcome()

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


@click.command()
@click.option(
    "--session",
    help="Session ID to resume previous conversation"
)
@click.option(
    "--mode",
    type=click.Choice(["local", "remote"], case_sensitive=False),
    help="Operation mode: 'local' (Phi-3 on-device) or 'remote' (Azure OpenAI)"
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
def main(session: Optional[str], mode: Optional[str], config: Optional[Path], debug: bool):
    """Interactive AI assistant for organizing screenshots.

    Supports two operation modes:

    LOCAL MODE:
      • Fully on-device with Phi-3 Vision MLX
      • Zero cost per query, complete privacy
      • No cloud dependencies or API keys needed
      • Requires: pip install phi-3-vision-mlx

    REMOTE MODE:
      • Azure OpenAI cloud-powered
      • More capable models (GPT-4, etc.)
      • Requires Azure credentials configured

    Mode Selection:
      • If --mode flag provided: Uses specified mode
      • If no flag: Interactive prompt at startup

    Required environment variables for REMOTE mode:
      AZURE_AI_CHAT_ENDPOINT - Your Azure endpoint (Foundry or Azure OpenAI)
      AZURE_AI_CHAT_KEY - Your API key (or use 'az login' for CLI auth)
      AZURE_AI_MODEL_DEPLOYMENT - Your deployed model name (e.g., gpt-4o)

    Supported endpoints:
      - AI Foundry: https://xxx.services.ai.azure.com/api/projects/xxx
      - Azure OpenAI: https://xxx.cognitiveservices.azure.com

    Get credentials from: https://ai.azure.com or Azure Portal
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

    # Interactive mode selection if not specified via CLI
    import os
    from utils.config import get_mode

    if mode is None:
        console = Console()
        console.print()
        console.print(Panel.fit(
            "[bold cyan]Screenshot Organizer[/bold cyan]\n\n"
            "Select operation mode:",
            border_style="cyan"
        ))
        console.print()
        console.print("[bold]1.[/bold] [green]Local Mode[/green] (Phi-3 Vision MLX)")
        console.print("   • Fully on-device, complete privacy")
        console.print("   • Zero cost per query")
        console.print("   • Requires: phi-3-vision-mlx package")
        console.print()
        console.print("[bold]2.[/bold] [cyan]Remote Mode[/cyan] (Azure OpenAI)")
        console.print("   • Cloud-powered, more capable")
        console.print("   • Requires: Azure credentials")
        console.print("   • ~$0.01-0.05 per query")
        console.print()

        choice = Prompt.ask(
            "[bold]Choose mode[/bold]",
            choices=["1", "2"],
            default="2"
        )

        mode = "local" if choice == "1" else "remote"
        console.print()
        logger.info(f"User selected {mode} mode")

    actual_mode = mode

    # Validate Azure credentials only for remote mode
    if actual_mode == "remote":
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
            console.print("Tip: Use [bold]--mode local[/bold] for fully on-device operation (no API keys needed)")
            sys.exit(1)

    # Create and run CLI
    try:
        cli = CLIInterface(session_id=session, mode=mode)
        asyncio.run(cli.chat_loop())
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        console = Console()
        console.print(f"[red]Fatal error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
