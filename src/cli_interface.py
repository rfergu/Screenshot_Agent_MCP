"""Interactive CLI interface for screenshot organization chat."""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from chat_client import ChatClient
from session_manager import SessionManager
from utils.config import load_config
from utils.logger import get_logger, setup_logging

logger = get_logger(__name__)


class CLIInterface:
    """Interactive command-line interface for screenshot organization."""

    def __init__(self, api_key: Optional[str] = None, session_id: Optional[str] = None):
        """Initialize CLI interface.

        Args:
            api_key: OpenAI API key. If None, reads from env.
            session_id: Optional session ID to resume. If None, creates new session.
        """
        self.console = Console()
        self.chat_client = ChatClient(api_key=api_key)
        self.session_manager = SessionManager()
        self.session_id = session_id or self.session_manager.create_session()
        
        # Load previous session if resuming
        if session_id:
            history = self.session_manager.load_session(session_id)
            if history:
                self.chat_client.conversation_history = history
                logger.info(f"Resumed session {session_id} with {len(history)} messages")

        logger.info(f"CLI initialized with session: {self.session_id}")

    def show_welcome(self):
        """Display welcome message and instructions."""
        welcome_text = """
[bold cyan]Screenshot Organizer AI Assistant[/bold cyan]

I can help you organize your screenshots using local AI models.

Commands:
  • Just chat naturally - ask me to analyze or organize screenshots
  • [bold]/help[/bold] - Show this help message
  • [bold]/clear[/bold] - Clear conversation history
  • [bold]/stats[/bold] - Show organization statistics
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
[bold cyan]/stats[/bold cyan] - Show organization statistics (file counts per category)
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

    def show_stats(self):
        """Display organization statistics."""
        try:
            stats = self.chat_client.tool_handlers.file_organizer.get_statistics()
            
            if not stats:
                self.console.print("[yellow]No organized files yet.[/yellow]\n")
                return

            self.console.print("\n[bold cyan]Organization Statistics:[/bold cyan]")
            total = sum(stats.values())
            
            for category, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
                bar_length = int((count / max(1, total)) * 30)
                bar = "█" * bar_length
                self.console.print(f"  {category:15} {count:4} {bar}")
            
            self.console.print(f"\n  [bold]Total: {total}[/bold]\n")
            
        except Exception as e:
            self.console.print(f"[red]Error getting statistics: {e}[/red]\n")
            logger.error(f"Error getting stats: {e}")

    def handle_command(self, user_input: str) -> bool:
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
            self.chat_client.reset_conversation()
            self.session_manager.clear_session(self.session_id)
            self.console.print("[green]✓ Conversation history cleared[/green]\n")
            return True

        if command == "/stats":
            self.show_stats()
            return True

        return False

    def chat_loop(self):
        """Main interactive chat loop."""
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
                    if self.handle_command(user_input):
                        if user_input.strip().lower() in ["/quit", "/exit"]:
                            break
                        continue

                # Send to chat client
                self.console.print()
                with self.console.status("[cyan]Thinking...[/cyan]", spinner="dots"):
                    response = self.chat_client.chat(user_input)

                # Display response
                self.console.print("[bold blue]Assistant[/bold blue]")
                self.chat_client.display_response(response)

                # Save session after each exchange
                self.session_manager.save_session(
                    self.session_id,
                    self.chat_client.conversation_history
                )

                # Check if we should truncate context
                if self.chat_client.should_truncate_context():
                    logger.info("Context length exceeded, truncating")
                    self.chat_client.truncate_context()

        except KeyboardInterrupt:
            self.console.print("\n\n[cyan]Interrupted. Goodbye! 👋[/cyan]")
        except Exception as e:
            self.console.print(f"\n[red]Error: {e}[/red]")
            logger.error(f"Chat loop error: {e}", exc_info=True)
        finally:
            # Save final session state
            self.session_manager.save_session(
                self.session_id,
                self.chat_client.conversation_history
            )
            logger.info("Session saved before exit")


@click.command()
@click.option(
    "--api-key",
    envvar="OPENAI_API_KEY",
    help="OpenAI API key (or set OPENAI_API_KEY env var)"
)
@click.option(
    "--session",
    help="Session ID to resume previous conversation"
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
def main(api_key: Optional[str], session: Optional[str], config: Optional[Path], debug: bool):
    """Interactive AI assistant for organizing screenshots.

    The assistant uses local AI models (OCR + Vision) to analyze screenshots
    and GPT-4 to orchestrate the organization process.
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

    # Validate API key
    if not api_key:
        console = Console()
        console.print("[red]Error: OpenAI API key not provided.[/red]")
        console.print("Set OPENAI_API_KEY environment variable or use --api-key option.")
        sys.exit(1)

    # Create and run CLI
    try:
        cli = CLIInterface(api_key=api_key, session_id=session)
        cli.chat_loop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        console = Console()
        console.print(f"[red]Fatal error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
