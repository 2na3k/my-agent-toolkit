"""Routing engine for orchestrating routing strategies."""

from typing import Any, Dict, Optional
from src.core import get_logger
from .models import RouteResult, RouteMatch
from .strategies.metadata import MetadataBasedStrategy


class RoutingEngine:
    """Orchestrates routing strategies to determine which agent handles input."""

    def __init__(self, default_agent: str = "hello_agent", confidence_threshold: float = 0.5):
        """
        Initialize routing engine.

        Args:
            default_agent: Fallback agent when no route matches
            confidence_threshold: Minimum confidence to accept a match (0.0-1.0)
        """
        self.default_agent = default_agent
        self.confidence_threshold = confidence_threshold
        self.logger = get_logger("router.engine")

        # Initialize strategies
        self.strategies = {
            'metadata': MetadataBasedStrategy(),
            # Future: 'llm_intent': LLMIntentStrategy()
        }

        self.logger.info(
            f"RoutingEngine initialized (default: {default_agent}, "
            f"threshold: {confidence_threshold})"
        )

    def route(self, input_data: Any, context: Optional[Dict] = None) -> RouteResult:
        """
        Execute strategies to determine routing.

        Args:
            input_data: Input to route
            context: Additional routing context

        Returns:
            RouteResult with routing decision
        """
        context = context or {}

        # Try metadata strategy first
        match = self.strategies['metadata'].match(input_data, context)

        if match.agent_type and match.confidence >= self.confidence_threshold:
            self.logger.info(
                f"Route matched: {match.agent_type} "
                f"(confidence: {match.confidence:.2f}, strategy: {match.strategy_name})"
            )
            return RouteResult(matched=True, route_match=match)

        # No match above threshold - use default agent
        self.logger.warning(
            f"No high-confidence route found (best: {match.confidence:.2f}), "
            f"using default: {self.default_agent}"
        )

        return RouteResult(
            matched=True,
            route_match=RouteMatch(
                agent_type=self.default_agent,
                confidence=0.5,
                metadata={'fallback': True, 'reason': 'no_match'},
                strategy_name='default'
            ),
            fallback_agent=self.default_agent
        )

    def add_strategy(self, name: str, strategy):
        """
        Add or replace a routing strategy.

        Args:
            name: Strategy name
            strategy: Strategy instance
        """
        self.strategies[name] = strategy
        self.logger.info(f"Added routing strategy: {name}")
