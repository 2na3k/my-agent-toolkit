"""Base class for routing strategies."""

from abc import ABC, abstractmethod
from typing import Any, Dict
from ..models import RouteMatch


class RoutingStrategy(ABC):
    """Abstract base class for routing strategies."""

    @abstractmethod
    def match(self, input_data: Any, context: Dict[str, Any]) -> RouteMatch:
        """
        Determine if strategy can route the input.

        Args:
            input_data: Input to be routed
            context: Additional routing context

        Returns:
            RouteMatch with routing decision
        """
        pass
