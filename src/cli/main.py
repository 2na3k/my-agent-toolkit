"""Main CLI entry point for the agent toolkit."""

import sys
from typing import Optional, List
from pathlib import Path

import typer
from rich.console import Console

from .chat_interface import ChatInterface
from .agent_invoker import AgentInvoker
from . import __version__

# Create Typer app
app = typer.Typer(
    name="aa",
    help="Agent Toolkit - CLI for AI agent interactions",
    add_completion=False,
)

console = Console()


@app.command()
def chat(
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        "-p",
        help="AI provider (claude, gemini, openai)",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        "-m",
        help="Model to use",
    ),
    no_router: bool = typer.Option(
        False,
        "--no-router",
        help="Disable router (pure LLM mode)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
):
    """Start an interactive chat session."""
    try:
        chat_interface = ChatInterface(
            provider=provider,
            model=model,
            use_router=not no_router,
            verbose=verbose,
        )
        chat_interface.start()
    except KeyboardInterrupt:
        console.print("\n[yellow]Chat interrupted by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error starting chat: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


@app.command()
def invoke(
    agent: str = typer.Option(
        ...,
        "--agent",
        "-a",
        help="Agent to invoke (e.g., hello_agent, convo)",
    ),
    message: str = typer.Option(
        ...,
        "--message",
        "-m",
        help="Message to send to the agent",
    ),
    files: Optional[List[Path]] = typer.Option(
        None,
        "--file",
        "-f",
        help="File(s) to attach",
        exists=True,
    ),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        "-p",
        help="AI provider (claude, gemini, openai)",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="Model to use",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Save output to file",
    ),
    format: str = typer.Option(
        "text",
        "--format",
        help="Output format (text, json)",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable verbose logging",
    ),
):
    """Invoke a specific agent with a message."""
    try:
        invoker = AgentInvoker(
            provider=provider,
            model=model,
            verbose=verbose,
        )

        result = invoker.invoke(
            agent_type=agent,
            message=message,
            files=files,
            output_format=format,
        )

        # Display or save result
        if output:
            output.write_text(result)
            console.print(f"[green]✓[/green] Output saved to {output}")
        else:
            invoker.display_result(result, format)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if verbose:
            console.print_exception()
        sys.exit(1)


@app.command()
def agents():
    """List available agents."""
    try:
        # Import here to avoid circular imports
        import src.agents  # noqa: F401
        from src.core import AgentFactory

        agent_list = AgentFactory.list_agents()

        console.print("\n[bold]Available Agents:[/bold]\n")

        for agent_type in sorted(agent_list):
            metadata = AgentFactory.get_metadata(agent_type)
            description = metadata.get("description", "No description")
            enabled = metadata.get("enabled", True)
            status = "[green]●[/green]" if enabled else "[dim]○[/dim]"

            console.print(f"{status} [cyan]{agent_type}[/cyan]")
            console.print(f"  {description}")

            if metadata.get("patterns"):
                console.print(f"  [dim]Patterns: {', '.join(metadata['patterns'][:3])}...[/dim]")
            console.print()

    except Exception as e:
        console.print(f"[red]Error listing agents: {e}[/red]")
        sys.exit(1)


@app.command()
def version():
    """Show version information."""
    console.print(f"[bold]Agent Toolkit[/bold] v{__version__}")
    console.print("A CLI for AI agent interactions")


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
