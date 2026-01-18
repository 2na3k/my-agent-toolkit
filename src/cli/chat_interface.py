"""Interactive chat interface (REPL)."""

import sys
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner

# Import agents to ensure registration
import src.agents  # noqa: F401
from src.core import AgentFactory

from .chat_commands import ChatCommands
from .output_formatter import OutputFormatter

console = Console()


class ChatInterface:
    """Interactive chat REPL."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        use_router: bool = True,
        verbose: bool = False,
    ):
        """
        Initialize chat interface.

        Args:
            provider: AI provider (claude, gemini, openai)
            model: Model to use
            use_router: Enable router for specialized agents
            verbose: Enable verbose logging
        """
        self.provider = provider
        self.model = model
        self.use_router = use_router
        self.verbose = verbose
        self.formatter = OutputFormatter()

        # Create ConvoAgent
        try:
            self.convo_agent = AgentFactory.create(
                "convo",
                provider=provider,
                model=model,
                use_router=use_router,
            )
        except Exception as e:
            console.print(f"[red]Failed to create conversation agent: {e}[/red]")
            if verbose:
                console.print_exception()
            sys.exit(1)

        # Initialize commands
        self.commands = ChatCommands(self.convo_agent)

    def start(self):
        """Start the interactive chat session."""
        self._show_welcome()

        while True:
            try:
                # Get user input
                user_input = self._get_input()

                if not user_input:
                    continue

                # Check for commands
                if self.commands.is_command(user_input):
                    should_exit = self.commands.execute(user_input)
                    if should_exit:
                        break
                    continue

                # Process message with agent
                response = self._process_message(user_input)

                # Display response
                self._display_response(response)

            except KeyboardInterrupt:
                console.print("\n[yellow]Use /exit to quit[/yellow]")
                continue
            except EOFError:
                console.print("\n[yellow]Goodbye! 👋[/yellow]")
                break
            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]")
                if self.verbose:
                    console.print_exception()

    def _show_welcome(self):
        """Show welcome message."""
        # Get provider and model info
        context = self.convo_agent.get_conversation_context()
        provider = context.get("provider", "unknown")
        model = context.get("model", "unknown")
        router_status = "enabled" if context.get("router_enabled") else "disabled"

        welcome_text = f"""[bold cyan]Agent Toolkit - Interactive Chat[/bold cyan]

[dim]Provider:[/dim] {provider}
[dim]Model:[/dim] {model}
[dim]Router:[/dim] {router_status}

Type your message to chat, or use commands:
  [cyan]/help[/cyan] - Show commands
  [cyan]/exit[/cyan] - Quit chat
"""

        panel = Panel(
            welcome_text,
            border_style="blue",
            padding=(1, 2),
        )

        console.print()
        console.print(panel)
        console.print()

    def _get_input(self) -> str:
        """Get user input."""
        try:
            user_input = console.input("[bold green]You:[/bold green] ")
            return user_input.strip()
        except (KeyboardInterrupt, EOFError):
            raise

    def _process_message(self, message: str) -> str:
        """
        Process message with ConvoAgent.

        Args:
            message: User message

        Returns:
            Agent response
        """
        # Show thinking indicator
        with Live(
            Spinner("dots", text="[dim]Thinking...[/dim]"),
            console=console,
            transient=True,
        ):
            try:
                response = self.convo_agent.run(message)
                return str(response)
            except Exception as e:
                raise Exception(f"Agent failed: {e}")

    def _display_response(self, response: str):
        """
        Display agent response.

        Args:
            response: Response text
        """
        console.print()
        console.print("[bold blue]Assistant:[/bold blue]")
        console.print()

        # Try to render as markdown if it looks like markdown
        if any(marker in response for marker in ["#", "**", "`", "```", "-", "*"]):
            try:
                md = Markdown(response)
                console.print(md)
            except Exception:
                # Fallback to plain text
                console.print(response)
        else:
            console.print(response)

        console.print()
