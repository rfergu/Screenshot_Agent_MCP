"""Main entry point for Screenshot Organizer application."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.config import load_config
from utils.logger import setup_logging
from utils.model_manager import ModelManager


@click.group()
@click.option(
    "--config",
    type=click.Path(exists=True, path_type=Path),
    help="Path to custom configuration file"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging"
)
@click.pass_context
def cli(ctx, config, debug):
    """Screenshot Organizer - AI-powered screenshot organization.

    Use local AI models (OCR + Vision) with GPT-4 orchestration to automatically
    categorize and organize your screenshots.
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Setup logging
    log_level = "DEBUG" if debug else "INFO"
    setup_logging(level=log_level)

    # Load configuration
    if config:
        # TODO: Support custom config file loading
        ctx.obj["config"] = load_config()
    else:
        ctx.obj["config"] = load_config()

    ctx.obj["debug"] = debug


@cli.command()
@click.option(
    "--api-key",
    envvar="OPENAI_API_KEY",
    required=True,
    help="OpenAI API key (or set OPENAI_API_KEY env var)"
)
@click.option(
    "--session",
    help="Session ID to resume previous conversation"
)
@click.pass_context
def chat(ctx, api_key, session):
    """Start interactive chat interface.

    Launch the conversational AI assistant for organizing screenshots.
    """
    from cli_interface import CLIInterface

    try:
        cli_interface = CLIInterface(api_key=api_key, session_id=session)
        cli_interface.chat_loop()
    except KeyboardInterrupt:
        console = Console()
        console.print("\n[cyan]Interrupted. Goodbye![/cyan]")
        sys.exit(0)
    except Exception as e:
        console = Console()
        console.print(f"[red]Error: {e}[/red]")
        if ctx.obj.get("debug"):
            raise
        sys.exit(1)


@cli.command()
@click.pass_context
def server(ctx):
    """Start MCP server.

    Run the Model Context Protocol server for tool integration.
    """
    import asyncio
    from screenshot_mcp_server import main as server_main

    try:
        asyncio.run(server_main())
    except KeyboardInterrupt:
        console = Console()
        console.print("\n[cyan]Server stopped.[/cyan]")
        sys.exit(0)
    except Exception as e:
        console = Console()
        console.print(f"[red]Error: {e}[/red]")
        if ctx.obj.get("debug"):
            raise
        sys.exit(1)


@cli.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--force-vision",
    is_flag=True,
    help="Force use of vision model instead of OCR"
)
@click.pass_context
def analyze(ctx, path, force_vision):
    """Analyze a single screenshot.

    Analyze PATH screenshot file and display categorization results.
    """
    from mcp_tools import MCPToolHandlers

    console = Console()

    try:
        handlers = MCPToolHandlers(ctx.obj["config"])

        console.print(f"\n[cyan]Analyzing: {path}[/cyan]")

        with console.status("[cyan]Processing...[/cyan]"):
            result = handlers.analyze_screenshot(str(path), force_vision=force_vision)

        # Display results
        console.print("\n[bold green]✓ Analysis Complete[/bold green]\n")

        table = Table(title="Screenshot Analysis")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Category", result["category"])
        table.add_row("Suggested Filename", result["suggested_filename"])
        table.add_row("Processing Method", result["processing_method"])
        table.add_row("Processing Time", f"{result['processing_time_ms']:.2f}ms")

        if result.get("description"):
            table.add_row("Description", result["description"])

        if result.get("extracted_text"):
            text_preview = result["extracted_text"][:100]
            if len(result["extracted_text"]) > 100:
                text_preview += "..."
            table.add_row("Extracted Text", text_preview)

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if ctx.obj.get("debug"):
            raise
        sys.exit(1)


@cli.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option(
    "--recursive",
    is_flag=True,
    help="Process subfolders recursively"
)
@click.option(
    "--organize",
    is_flag=True,
    help="Automatically organize files after analysis"
)
@click.option(
    "--max-files",
    type=int,
    help="Maximum number of files to process"
)
@click.pass_context
def batch(ctx, folder, recursive, organize, max_files):
    """Process all screenshots in a folder.

    Analyze all screenshots in FOLDER and optionally organize them.
    """
    from mcp_tools import MCPToolHandlers

    console = Console()

    try:
        handlers = MCPToolHandlers(ctx.obj["config"])

        console.print(f"\n[cyan]Processing folder: {folder}[/cyan]")
        console.print(f"Recursive: {recursive}, Organize: {organize}\n")

        with console.status("[cyan]Processing screenshots...[/cyan]"):
            stats = handlers.batch_process(
                folder=str(folder),
                recursive=recursive,
                max_files=max_files,
                organize=organize
            )

        # Display results
        console.print("\n[bold green]✓ Batch Processing Complete[/bold green]\n")

        table = Table(title="Batch Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Files", str(stats["total_files"]))
        table.add_row("Successful", str(stats["successful"]))
        table.add_row("Failed", str(stats["failed"]))
        table.add_row("OCR Processed", str(stats["ocr_processed"]))
        table.add_row("Vision Processed", str(stats["vision_processed"]))
        table.add_row("Total Time", f"{stats['total_time_ms']:.2f}ms")
        table.add_row("Avg per File", f"{stats['average_time_per_file_ms']:.2f}ms")

        console.print(table)

        # Category breakdown
        if stats["categories_count"]:
            console.print("\n[bold]Categories:[/bold]")
            for category, count in sorted(stats["categories_count"].items()):
                console.print(f"  {category}: {count}")

        # Errors
        if stats["errors"]:
            console.print(f"\n[yellow]Errors ({len(stats['errors'])}):[/yellow]")
            for error in stats["errors"][:5]:
                console.print(f"  • {error['file_path']}: {error['error_message']}")
            if len(stats["errors"]) > 5:
                console.print(f"  ... and {len(stats['errors']) - 5} more")

        console.print()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if ctx.obj.get("debug"):
            raise
        sys.exit(1)


@cli.command()
@click.pass_context
def check(ctx):
    """Check system requirements.

    Verify that all required dependencies and models are available.
    """
    console = Console()

    console.print("\n[bold cyan]System Requirements Check[/bold cyan]\n")

    # Check model manager
    model_manager = ModelManager()
    requirements = model_manager.check_requirements()

    # Display results
    table = Table(title="Model Availability")
    table.add_column("Model", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Required", style="yellow")
    table.add_column("Name", style="white")

    for key, info in requirements["models"].items():
        status = "✓ Available" if info["available"] else "✗ Missing"
        status_style = "green" if info["available"] else "red"
        required = "Yes" if info["required"] else "No"

        table.add_row(
            key,
            f"[{status_style}]{status}[/{status_style}]",
            required,
            info["name"]
        )

    console.print(table)

    # Overall status
    if requirements["all_required_available"]:
        console.print("\n[bold green]✓ All required models are available![/bold green]\n")
    else:
        console.print("\n[bold red]✗ Some required models are missing.[/bold red]\n")

    # Suggestions
    suggestions = model_manager.suggest_actions()
    if suggestions:
        console.print("[bold yellow]Suggested Actions:[/bold yellow]")
        for suggestion in suggestions:
            console.print(f"  • {suggestion}")
        console.print()

    # Cache info
    cache_size = model_manager.get_cache_size()
    console.print(f"Model cache size: {cache_size:.2f} MB")
    console.print(f"Cache location: {model_manager.cache_dir}\n")


@cli.command()
def version():
    """Show version information."""
    from src import __version__

    console = Console()
    console.print(f"\n[bold cyan]Screenshot Organizer[/bold cyan] version [green]{__version__}[/green]\n")


def main():
    """Main entry point."""
    try:
        cli(obj={})
    except Exception as e:
        console = Console()
        console.print(f"[red]Fatal error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
