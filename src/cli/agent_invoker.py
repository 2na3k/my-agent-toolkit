"""Agent invoker for direct mode."""

from typing import Optional, List, Any
from pathlib import Path

from rich.console import Console

# Import agents to ensure registration
import src.agents  # noqa: F401
from src.core import AgentFactory

from .file_handler import FileHandler
from .output_formatter import OutputFormatter

console = Console()


class AgentInvoker:
    """Handle direct agent invocation (one-shot mode)."""

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        verbose: bool = False,
    ):
        """
        Initialize agent invoker.

        Args:
            provider: AI provider (claude, gemini, openai)
            model: Model to use
            verbose: Enable verbose logging
        """
        self.provider = provider
        self.model = model
        self.verbose = verbose
        self.formatter = OutputFormatter()

    def invoke(
        self,
        agent_type: str,
        message: str,
        files: Optional[List[Path]] = None,
        output_format: str = "text",
    ) -> str:
        """
        Invoke an agent with a message and optional files.

        Args:
            agent_type: Type of agent to invoke
            message: Message to send
            files: Optional list of file paths to attach
            output_format: Output format (text, json)

        Returns:
            Formatted result string

        Raises:
            ValueError: If agent not found or invocation fails
        """
        # Check if agent exists
        if not AgentFactory.is_registered(agent_type):
            available = AgentFactory.list_agents()
            raise ValueError(
                f"Agent '{agent_type}' not found. "
                f"Available agents: {', '.join(available)}"
            )

        # Process files if provided
        file_data = []
        if files:
            console.print(f"[dim]Processing {len(files)} file(s)...[/dim]")
            for file_path in files:
                try:
                    data = FileHandler.read_file(file_path)
                    file_data.append(data)
                    if self.verbose:
                        info = FileHandler.format_file_info(data)
                        console.print(f"[dim]  {info}[/dim]")
                except Exception as e:
                    raise ValueError(f"Failed to read file {file_path}: {e}")

        # Create agent
        if self.verbose:
            console.print(f"[dim]Creating agent: {agent_type}[/dim]")
            if self.provider:
                console.print(f"[dim]Provider: {self.provider}[/dim]")
            if self.model:
                console.print(f"[dim]Model: {self.model}[/dim]")

        try:
            agent = AgentFactory.create(
                agent_type=agent_type,
                provider=self.provider,
                model=self.model,
            )
        except Exception as e:
            raise ValueError(f"Failed to create agent: {e}")

        # Prepare input
        input_data = message
        kwargs = {}

        # Add file data to kwargs if present
        if file_data:
            kwargs["files"] = file_data

        # Execute agent
        if self.verbose:
            console.print(f"[dim]Executing agent...[/dim]")

        try:
            result = agent.run(input_data, **kwargs)
        except Exception as e:
            raise ValueError(f"Agent execution failed: {e}")

        # Format result
        if output_format == "json":
            return self.formatter.format_json(result)
        else:
            return self.formatter.format_text(str(result))

    def display_result(self, result: str, format: str = "text"):
        """
        Display result to console.

        Args:
            result: Result to display
            format: Output format (text, json)
        """
        console.print()  # Blank line

        if format == "json":
            self.formatter.display_json(result, title="Result")
        else:
            self.formatter.display_text(result, title="Result")

        console.print()  # Blank line
