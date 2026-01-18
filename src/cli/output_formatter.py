"""Output formatting utilities for CLI."""

import json
from typing import Any, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.panel import Panel

console = Console()


class OutputFormatter:
    """Format and display agent output."""

    @staticmethod
    def format_text(content: str) -> str:
        """Format text output."""
        return content

    @staticmethod
    def format_json(content: Any) -> str:
        """Format as JSON."""
        if isinstance(content, str):
            # Try to parse if it's a JSON string
            try:
                parsed = json.loads(content)
                return json.dumps(parsed, indent=2)
            except json.JSONDecodeError:
                # Not JSON, wrap in object
                return json.dumps({"result": content}, indent=2)
        else:
            return json.dumps(content, indent=2)

    @staticmethod
    def display_text(content: str, title: Optional[str] = None):
        """Display text with Rich formatting."""
        if title:
            console.print(Panel(content, title=title, border_style="green"))
        else:
            # Try to detect markdown
            if any(marker in content for marker in ["#", "**", "`", "```", "-", "*"]):
                md = Markdown(content)
                console.print(md)
            else:
                console.print(content)

    @staticmethod
    def display_json(content: Any, title: Optional[str] = None):
        """Display JSON with syntax highlighting."""
        json_str = OutputFormatter.format_json(content)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)

        if title:
            console.print(Panel(syntax, title=title, border_style="blue"))
        else:
            console.print(syntax)

    @staticmethod
    def display_error(message: str, exception: Optional[Exception] = None):
        """Display error message."""
        console.print(f"[bold red]Error:[/bold red] {message}")
        if exception:
            console.print(f"[dim]{str(exception)}[/dim]")

    @staticmethod
    def display_success(message: str):
        """Display success message."""
        console.print(f"[bold green]✓[/bold green] {message}")

    @staticmethod
    def display_info(message: str):
        """Display info message."""
        console.print(f"[bold blue]ℹ[/bold blue] {message}")

    @staticmethod
    def display_warning(message: str):
        """Display warning message."""
        console.print(f"[bold yellow]⚠[/bold yellow] {message}")
