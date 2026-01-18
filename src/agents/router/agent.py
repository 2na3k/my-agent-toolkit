"""Router agent for routing inputs to specialized agents."""

from typing import Any, Optional, Dict
from src.core import BaseAgent, register_agent
from .engine import RoutingEngine
from .executor import RouteExecutor
from .models import RouteResult


@register_agent(
    "router",
    patterns=[],  # Router doesn't route to itself
    description="Routes inputs to specialized agents based on metadata",
    enabled=False  # Exclude from routing (prevents infinite loop)
)
class RouterAgent(BaseAgent):
    """
    Router agent that routes inputs to specialized agents.

    Uses a routing engine with pluggable strategies to determine
    which agent should handle each input.
    """

    def __init__(
        self,
        name: str = "RouterAgent",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        config_path: Optional[str] = None,
        default_agent: str = "hello_agent",
        confidence_threshold: float = 0.5,
        **kwargs
    ):
        super().__init__(
            name=name,
            provider=provider,
            model=model,
            config_path=config_path,
            **kwargs
        )

        # Initialize routing components
        self.engine = RoutingEngine(
            default_agent=default_agent,
            confidence_threshold=confidence_threshold
        )
        self.executor = RouteExecutor()

        self.logger.info(
            f"RouterAgent initialized (default: {default_agent}, "
            f"threshold: {confidence_threshold})"
        )

    def run(self, input_data: Any, **kwargs) -> Any:
        """
        Route input to appropriate agent and return result.

        Args:
            input_data: Input to route
            **kwargs: Additional context for routing and execution

        Returns:
            Result from the routed agent
        """
        # Get routing context from kwargs
        context = kwargs.get('context', {})

        # Determine route
        route_result = self.route(input_data, context)

        # Store routing info in state
        self._store_routing_info(route_result)

        # Execute routed agent
        result = self.execute_route(route_result, input_data, **kwargs)

        return result

    def route(self, input_data: Any, context: Optional[Dict] = None) -> RouteResult:
        """
        Determine which agent should handle the input.

        Args:
            input_data: Input to route
            context: Additional routing context

        Returns:
            RouteResult with routing decision
        """
        self.logger.debug(f"Routing input: {str(input_data)[:100]}...")

        route_result = self.engine.route(input_data, context)

        if route_result.matched:
            self.logger.info(
                f"Routed to {route_result.route_match.agent_type} "
                f"(strategy: {route_result.route_match.strategy_name}, "
                f"confidence: {route_result.route_match.confidence:.2f})"
            )
        else:
            self.logger.warning(f"No route matched: {route_result.error}")

        return route_result

    def execute_route(self, route_result: RouteResult, input_data: Any, **kwargs) -> Any:
        """
        Execute the routed agent.

        Args:
            route_result: Result from routing
            input_data: Input for the agent
            **kwargs: Additional execution parameters

        Returns:
            Result from the routed agent
        """
        return self.executor.execute(route_result, input_data, **kwargs)

    def _store_routing_info(self, route_result: RouteResult):
        """Store routing information in agent state."""
        if route_result.matched:
            routing_info = {
                'agent': route_result.route_match.agent_type,
                'strategy': route_result.route_match.strategy_name,
                'confidence': route_result.route_match.confidence,
                'metadata': route_result.route_match.metadata,
                'is_fallback': route_result.fallback_agent is not None
            }
            self.set_state('last_route', routing_info)

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get statistics about routing decisions."""
        last_route = self.get_state('last_route')
        return {
            'last_route': last_route,
            'available_strategies': list(self.engine.strategies.keys()),
            'default_agent': self.engine.default_agent
        }
