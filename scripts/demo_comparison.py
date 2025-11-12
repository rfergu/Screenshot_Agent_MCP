#!/usr/bin/env python
"""Demo comparison utility showing local vs remote mode side-by-side.

This script demonstrates the dual-mode capabilities of the screenshot organizer
by running the same query through both local (Phi-3) and remote (Azure OpenAI)
modes and comparing results.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agent_client import AgentClient
from utils.logger import setup_logging


async def run_query_comparison(query: str, show_latency: bool = True):
    """Run the same query through both local and remote modes.

    Args:
        query: The query to run through both modes.
        show_latency: Whether to show response latency.
    """
    console = Console()

    console.print()
    console.print(Panel.fit(
        f"[bold cyan]Demo Comparison[/bold cyan]\n\n"
        f"Running the same query through both modes:\n"
        f"[yellow]'{query}'[/yellow]",
        border_style="cyan"
    ))
    console.print()

    # Create table for comparison
    table = Table(title="Local vs Remote Comparison", show_header=True, header_style="bold magenta")
    table.add_column("Mode", style="cyan", width=12)
    table.add_column("Model", style="green", width=20)
    table.add_column("Response", width=60)
    if show_latency:
        table.add_column("Latency", style="yellow", width=10)

    # Run local mode
    console.print("[bold green]🏠 Running in LOCAL mode (Phi-3)...[/bold green]")
    try:
        local_client = AgentClient(mode="local")
        local_thread = local_client.get_new_thread()

        start_time = time.time()
        local_response = await local_client.chat(query, thread=local_thread)
        local_latency = time.time() - start_time

        local_model = local_client.model_name
        console.print("[green]✓ Local response received[/green]\n")
    except Exception as e:
        local_response = f"[red]Error: {str(e)}[/red]"
        local_latency = 0
        local_model = "N/A"
        console.print(f"[red]✗ Local mode failed: {e}[/red]\n")

    # Run remote mode
    console.print("[bold cyan]☁️  Running in REMOTE mode (Azure OpenAI)...[/bold cyan]")
    try:
        remote_client = AgentClient(mode="remote")
        remote_thread = remote_client.get_new_thread()

        start_time = time.time()
        remote_response = await remote_client.chat(query, thread=remote_thread)
        remote_latency = time.time() - start_time

        remote_model = remote_client.model_name
        console.print("[cyan]✓ Remote response received[/cyan]\n")
    except Exception as e:
        remote_response = f"[red]Error: {str(e)}[/red]"
        remote_latency = 0
        remote_model = "N/A"
        console.print(f"[red]✗ Remote mode failed: {e}[/red]\n")

    # Add rows to table
    local_row = [
        "🏠 Local",
        local_model,
        local_response[:200] + "..." if len(local_response) > 200 else local_response
    ]
    remote_row = [
        "☁️  Remote",
        remote_model,
        remote_response[:200] + "..." if len(remote_response) > 200 else remote_response
    ]

    if show_latency:
        local_row.append(f"{local_latency:.2f}s")
        remote_row.append(f"{remote_latency:.2f}s")

    table.add_row(*local_row)
    table.add_row(*remote_row)

    # Display comparison
    console.print(table)
    console.print()

    # Show full responses in panels
    console.print(Panel(
        local_response,
        title="[bold green]🏠 Local Mode Response (Phi-3 Vision MLX)[/bold green]",
        border_style="green"
    ))
    console.print()

    console.print(Panel(
        remote_response,
        title="[bold cyan]☁️  Remote Mode Response (Azure OpenAI)[/bold cyan]",
        border_style="cyan"
    ))
    console.print()

    # Show summary
    summary = f"""
[bold]Summary:[/bold]

🏠 [green]LOCAL MODE[/green]:
  • Model: {local_model}
  • Latency: {local_latency:.2f}s
  • Cost: $0.00 (fully local)
  • Privacy: Complete (no data leaves device)

☁️  [cyan]REMOTE MODE[/cyan]:
  • Model: {remote_model}
  • Latency: {remote_latency:.2f}s
  • Cost: ~$0.01-0.05 per query (varies by model)
  • Privacy: Data processed in Azure cloud
    """

    console.print(Panel(summary, title="Comparison Summary", border_style="magenta"))


async def main():
    """Main demo comparison entry point."""
    console = Console()

    # Setup logging
    setup_logging(level="INFO")

    # Welcome
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Screenshot Organizer - Mode Comparison Demo[/bold cyan]\n\n"
        "This demo compares LOCAL (Phi-3) vs REMOTE (Azure OpenAI) modes\n"
        "by running the same query through both and showing results side-by-side.",
        border_style="cyan"
    ))
    console.print()

    # Example queries for demonstration
    demo_queries = [
        "What categories do you support for organizing screenshots?",
        "How do you analyze screenshots?",
        "What's the difference between OCR and vision model analysis?"
    ]

    # Let user choose a query or provide their own
    console.print("[bold]Demo Queries:[/bold]")
    for i, query in enumerate(demo_queries, 1):
        console.print(f"  {i}. {query}")
    console.print("  4. Custom query")
    console.print()

    choice = console.input("[bold green]Select a demo query (1-4):[/bold green] ").strip()

    if choice == "4":
        query = console.input("[bold green]Enter your query:[/bold green] ").strip()
    elif choice in ["1", "2", "3"]:
        query = demo_queries[int(choice) - 1]
    else:
        console.print("[red]Invalid choice. Using default query.[/red]")
        query = demo_queries[0]

    # Run comparison
    await run_query_comparison(query, show_latency=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console = Console()
        console.print("\n[cyan]Demo interrupted. Goodbye! 👋[/cyan]")
        sys.exit(0)
    except Exception as e:
        console = Console()
        console.print(f"\n[red]Error: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        sys.exit(1)
