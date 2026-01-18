from typing import Any, Optional

from src.core import BaseAgent, register_agent


@register_agent(
    "hello_agent",
    patterns=[r".*"],  # Match everything for now (will be more specific later)
    keywords=["hello", "hi", "greet", "greeting"],
    description="A simple agent that always returns 'hello'",
    priority=0,
)
class HelloAgent(BaseAgent):
    """
    Hello Agent - A simple agent that always returns 'hello'.

    This agent demonstrates the basic usage of BaseAgent and always
    returns "hello" regardless of the input provided.
    """

    def __init__(
        self,
        name: str = "HelloAgent",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        config_path: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize the Hello Agent.

        Args:
            name: Agent name (default: "HelloAgent")
            provider: AI provider (not used in this simple agent)
            model: Model to use (not used in this simple agent)
            config_path: Path to config file (not used in this simple agent)
            **kwargs: Additional arguments
        """
        # Initialize base agent (even though we won't use the AI client)
        super().__init__(
            name=name, provider=provider, model=model, config_path=config_path, **kwargs
        )

        self.logger.info("HelloAgent initialized - will always return 'hello'")

    def run(self, input_data: Any, **kwargs) -> str:
        """
        Process input and return 'hello'.

        This method always returns "hello" regardless of input,
        as specified in the README.

        Args:
            input_data: Any input data (ignored)
            **kwargs: Additional parameters (ignored)

        Returns:
            Always returns the string "hello"
        """
        self.logger.debug(f"Received input: {input_data}")
        self.logger.info("Returning 'hello'")

        # Store the input in state for tracking
        self.set_state("last_input", input_data)

        return "hello"

    def greet(self, name: Optional[str] = None) -> str:
        """
        Optional greeting method that can personalize the hello.

        Args:
            name: Optional name to greet

        Returns:
            Greeting string
        """
        if name:
            greeting = f"hello, {name}!"
            self.logger.info(f"Personalized greeting: {greeting}")
            return greeting

        return self.run(None)
