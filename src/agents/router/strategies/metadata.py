"""Metadata-based routing strategy."""

import re
from typing import Any, Dict
from src.core import AgentFactory, get_logger
from .base import RoutingStrategy
from ..models import RouteMatch


class MetadataBasedStrategy(RoutingStrategy):
    """Routing strategy that uses agent metadata from AgentFactory."""

    def __init__(self):
        self.logger = get_logger("router.strategy.metadata")

    def match(self, input_data: Any, context: Dict[str, Any]) -> RouteMatch:
        """
        Match input against all registered agents' patterns and keywords.

        Returns highest-confidence match based on:
        - Pattern matching (regex)
        - Keyword matching
        - Agent priority

        Args:
            input_data: Input to be routed
            context: Additional routing context

        Returns:
            RouteMatch with routing decision
        """
        input_str = str(input_data).strip()

        # Get all routable agents sorted by priority (highest first)
        agents_metadata = AgentFactory.get_routable_agents()
        sorted_agents = sorted(
            agents_metadata.items(),
            key=lambda x: x[1].get('priority', 0),
            reverse=True
        )

        matches = []

        for agent_type, metadata in sorted_agents:
            # Check pattern matching
            patterns = metadata.get('patterns', [])
            for pattern in patterns:
                try:
                    if re.search(pattern, input_str, re.IGNORECASE):
                        confidence = 1.0  # Exact pattern match
                        matches.append((
                            agent_type,
                            confidence,
                            {'matched_pattern': pattern, 'match_type': 'pattern'},
                            metadata.get('priority', 0)
                        ))
                        break  # Found a match for this agent
                except re.error as e:
                    self.logger.warning(f"Invalid regex pattern '{pattern}' for {agent_type}: {e}")

            # Check keyword matching (only if no pattern matched)
            if not matches or matches[-1][0] != agent_type:
                keywords = metadata.get('keywords', [])
                matched_keywords = [kw for kw in keywords if kw.lower() in input_str.lower()]

                if matched_keywords:
                    # Confidence based on keyword match ratio
                    confidence = len(matched_keywords) / max(len(keywords), 1) * 0.8
                    matches.append((
                        agent_type,
                        confidence,
                        {'matched_keywords': matched_keywords, 'match_type': 'keyword'},
                        metadata.get('priority', 0)
                    ))

        if not matches:
            return RouteMatch(None, 0.0, {}, 'metadata')

        # Return highest confidence match (with priority as tiebreaker)
        best_match = max(matches, key=lambda x: (x[1], x[3]))  # Sort by confidence, then priority
        agent_type, confidence, metadata, _ = best_match

        self.logger.info(f"Matched {agent_type} with confidence {confidence:.2f}")

        return RouteMatch(
            agent_type=agent_type,
            confidence=confidence,
            metadata=metadata,
            strategy_name='metadata'
        )
