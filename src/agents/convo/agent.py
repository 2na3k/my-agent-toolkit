"""Conversation agent - main entry point for chat workflow."""

from typing import Any, Optional, Dict
from src.core import BaseAgent, register_agent, AgentFactory


@register_agent(
    "convo",
    patterns=[],  # Convo agent is the default entry point, not routed to
    description="Main conversation agent that orchestrates chat workflow",
    enabled=False,  # Exclude from routing (it IS the entry point)
)
class ConvoAgent(BaseAgent):
    """
    Conversation Agent - Main entry point for chat workflow.

    Orchestrates the chat workflow by:
    1. Checking if input should be routed to specialized agents
    2. If yes, delegates to specialized agent via RouterAgent
    3. If no, handles conversation directly using LLM
    """

    def __init__(
        self,
        name: str = "ConvoAgent",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        config_path: Optional[str] = None,
        use_router: bool = True,
        router_confidence_threshold: float = 0.7,
        **kwargs,
    ):
        """
        Initialize the Conversation Agent.

        Args:
            name: Agent name (default: "ConvoAgent")
            provider: AI provider for LLM conversations
            model: Model to use for LLM conversations
            config_path: Path to config file
            use_router: Whether to use router for intent detection (default: True)
            router_confidence_threshold: Minimum confidence to route to specialized agent
            **kwargs: Additional arguments
        """
        super().__init__(
            name=name,
            provider=provider,
            model=model,
            config_path=config_path,
            **kwargs,
        )

        self.use_router = use_router
        self.router_confidence_threshold = router_confidence_threshold

        # Initialize router for intent detection
        if self.use_router:
            try:
                self.router = AgentFactory.create(
                    "router",
                    provider=provider,
                    model=model,
                    config_path=config_path,
                    confidence_threshold=router_confidence_threshold,
                )
                self.logger.info(
                    f"Router initialized with confidence threshold: {router_confidence_threshold}"
                )
            except Exception as e:
                self.logger.warning(f"Failed to initialize router: {e}. Falling back to LLM only.")
                self.use_router = False
                self.router = None
        else:
            self.router = None

        self.logger.info(
            f"ConvoAgent initialized (use_router: {self.use_router}, "
            f"provider: {self.client.current_provider})"
        )

    def run(self, input_data: Any, **kwargs) -> Any:
        """
        Main conversation workflow.

        Workflow:
        1. Check if input should be routed to specialized agent
        2. If high-confidence route found, use specialized agent
        3. Otherwise, handle with direct LLM conversation

        Args:
            input_data: User input (text message)
            **kwargs: Additional context

        Returns:
            Response from specialized agent or LLM
        """
        input_text = str(input_data)
        self.logger.info(f"Processing input: {input_text[:100]}...")

        # Store input in state
        self.set_state("last_input", input_text)

        # Try routing to specialized agent if router is enabled
        if self.use_router and self.router:
            try:
                route_result = self.router.route(input_text, kwargs.get("context", {}))

                # Check if we have a high-confidence route to a specialized agent (not fallback)
                if (
                    route_result.matched
                    and not route_result.fallback_agent
                    and route_result.route_match.confidence >= self.router_confidence_threshold
                ):
                    agent_type = route_result.route_match.agent_type
                    self.logger.info(
                        f"Routing to specialized agent: {agent_type} "
                        f"(confidence: {route_result.route_match.confidence:.2f})"
                    )

                    # Execute the specialized agent
                    result = self.router.execute_route(route_result, input_text, **kwargs)

                    # Store routing info
                    self.set_state("last_route", {
                        "agent": agent_type,
                        "confidence": route_result.route_match.confidence,
                        "strategy": route_result.route_match.strategy_name,
                    })

                    return result

                else:
                    # Low confidence or fallback - use LLM directly
                    self.logger.info("No high-confidence specialized agent route, using LLM conversation")

            except Exception as e:
                self.logger.warning(f"Routing failed: {e}. Falling back to LLM conversation.")

        # Fallback to direct LLM conversation
        return self._handle_llm_conversation(input_text, **kwargs)

    def _handle_llm_conversation(self, input_text: str, **kwargs) -> str:
        """
        Handle conversation directly with LLM.

        Args:
            input_text: User input
            **kwargs: Additional parameters for chat

        Returns:
            LLM response
        """
        self.logger.info("Handling conversation with LLM")

        # Get conversation parameters
        temperature = kwargs.get("temperature", 0.7)
        max_tokens = kwargs.get("max_tokens", 2000)

        # Use the chat method which maintains conversation history
        response = self.chat(
            message=input_text,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Extract response text
        if hasattr(response, "choices") and response.choices:
            response_text = response.choices[0].message.content
            self.logger.debug(f"LLM response: {response_text[:100]}...")
            return response_text

        return str(response)

    def get_conversation_context(self) -> Dict[str, Any]:
        """
        Get current conversation context.

        Returns:
            Dictionary with conversation state and history
        """
        last_route = self.get_state("last_route")

        return {
            "history_length": len(self.history),
            "last_input": self.get_state("last_input"),
            "last_route": last_route,
            "provider": self.client.current_provider,
            "model": self.model or self.client.get_default_model(),
            "router_enabled": self.use_router,
        }

    def reset_conversation(self):
        """Reset conversation history and state."""
        self.clear_history()
        self.reset_state()
        self.logger.info("Conversation reset")
