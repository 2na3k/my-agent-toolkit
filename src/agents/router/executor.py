"""Route executor for managing agent lifecycle and execution."""

from typing import Any
from src.core import AgentFactory, get_logger
from .models import RouteResult


class RouteExecutor:
    """Manages agent creation and execution for routed requests."""

    def __init__(self):
        self.logger = get_logger("router.executor")
        self._agent_cache = {}  # Optional: cache agents

    def execute(self, route_result: RouteResult, input_data: Any, **kwargs) -> Any:
        """
        Create target agent and execute its run method.

        Args:
            route_result: Result from routing engine
            input_data: Input data for the agent
            **kwargs: Additional execution parameters

        Returns:
            Result from the executed agent

        Raises:
            ValueError: If route result is not matched
        """
        if not route_result.matched:
            raise ValueError(f"Cannot execute unmatched route: {route_result.error}")

        agent_type = route_result.route_match.agent_type

        try:
            # Create agent via factory
            agent = AgentFactory.create(
                agent_type=agent_type, name=f"routed_{agent_type}", **kwargs
            )

            self.logger.info(f"Executing agent: {agent_type}")

            # Execute and return result
            result = agent.run(input_data, **kwargs)

            return result

        except Exception as e:
            self.logger.error(f"Failed to execute agent {agent_type}: {e}")
            raise
