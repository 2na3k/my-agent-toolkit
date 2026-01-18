"""Special commands for interactive chat mode."""

from typing import Optional, Callable
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


class ChatCommands:
    """Handle special chat commands."""

    def __init__(self, convo_agent):
        """
        Initialize chat commands.

        Args:
            convo_agent: ConvoAgent instance to control
        """
        self.convo_agent = convo_agent
        self.commands = {
            "/help": self.help_command,
            "/h": self.help_command,
            "/exit": self.exit_command,
            "/quit": self.exit_command,
            "/q": self.exit_command,
            "/reset": self.reset_command,
            "/clear": self.reset_command,
            "/context": self.context_command,
            "/c": self.context_command,
            "/agents": self.agents_command,
            "/history": self.history_command,
        }

    def is_command(self, input_text: str) -> bool:
        """Check if input is a command."""
        return input_text.strip().startswith("/")

    def execute(self, input_text: str) -> Optional[bool]:
        """
        Execute a command.

        Args:
            input_text: User input

        Returns:
            True to exit chat, False to continue, None if not a command
        """
        command_parts = input_text.strip().split(maxsplit=1)
        command = command_parts[0].lower()
        args = command_parts[1] if len(command_parts) > 1 else None

        if command in self.commands:
            return self.commands[command](args)

        # Unknown command
        console.print(f"[yellow]Unknown command: {command}[/yellow]")
        console.print("Type [cyan]/help[/cyan] for available commands")
        return False

    def help_command(self, args: Optional[str] = None) -> bool:
        """Show help information."""
        table = Table(title="Available Commands", show_header=True)
        table.add_column("Command", style="cyan")
        table.add_column("Description", style="white")

        table.add_row("/help, /h", "Show this help message")
        table.add_row("/exit, /quit, /q", "Exit the chat")
        table.add_row("/reset, /clear", "Reset conversation history")
        table.add_row("/context, /c", "Show conversation context")
        table.add_row("/agents", "List available agents")
        table.add_row("/history", "Show conversation history")

        console.print()
        console.print(table)
        console.print()
        console.print("[dim]Tip: Just type your message to chat normally[/dim]")
        console.print()

        return False  # Continue chat

    def exit_command(self, args: Optional[str] = None) -> bool:
        """Exit the chat."""
        console.print("\n[yellow]Goodbye! 👋[/yellow]\n")
        return True  # Exit chat

    def reset_command(self, args: Optional[str] = None) -> bool:
        """Reset conversation."""
        self.convo_agent.reset_conversation()
        console.print("[green]✓[/green] Conversation reset")
        return False  # Continue chat

    def context_command(self, args: Optional[str] = None) -> bool:
        """Show conversation context."""
        context = self.convo_agent.get_conversation_context()

        table = Table(title="Conversation Context", show_header=False)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("History Length", str(context.get("history_length", 0)))
        table.add_row("Provider", context.get("provider", "unknown"))
        table.add_row("Model", context.get("model", "unknown"))
        table.add_row("Router Enabled", str(context.get("router_enabled", False)))

        last_route = context.get("last_route")
        if last_route:
            table.add_row("Last Route Agent", last_route.get("agent", "N/A"))
            table.add_row("Last Route Confidence", f"{last_route.get('confidence', 0):.2f}")

        console.print()
        console.print(table)
        console.print()

        return False  # Continue chat

    def agents_command(self, args: Optional[str] = None) -> bool:
        """List available agents."""
        from src.core import AgentFactory

        routable = AgentFactory.get_routable_agents()
        all_agents = AgentFactory.list_agents()

        console.print()
        console.print("[bold]Available Agents:[/bold]")
        console.print()

        for agent_type in sorted(all_agents):
            metadata = AgentFactory.get_metadata(agent_type)
            is_routable = agent_type in routable

            status = "[green]●[/green]" if is_routable else "[dim]○[/dim]"
            console.print(f"{status} [cyan]{agent_type}[/cyan]")

            description = metadata.get("description", "No description")
            console.print(f"  {description}")
            console.print()

        return False  # Continue chat

    def history_command(self, args: Optional[str] = None) -> bool:
        """Show conversation history."""
        history = self.convo_agent.history

        if not history:
            console.print("[yellow]No conversation history[/yellow]")
            return False

        console.print()
        console.print(f"[bold]Conversation History ({len(history)} exchanges):[/bold]")
        console.print()

        for i, entry in enumerate(history, 1):
            user_msg = entry.get("user", "")
            assistant_msg = entry.get("assistant", "")

            console.print(f"[cyan]Exchange {i}:[/cyan]")
            console.print(f"  [bold]You:[/bold] {user_msg[:100]}...")
            if assistant_msg:
                console.print(f"  [bold]Assistant:[/bold] {assistant_msg[:100]}...")
            console.print()

        return False  # Continue chat
