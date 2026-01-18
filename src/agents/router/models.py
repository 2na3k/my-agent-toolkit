"""Data models for router agent."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class RouteMatch:
    """Represents a successful route match."""
    agent_type: str           # e.g., "hello_agent"
    confidence: float         # 0.0 to 1.0
    metadata: Dict[str, Any]  # Pattern matched, keywords, etc.
    strategy_name: str        # Which strategy produced this match


@dataclass
class RouteResult:
    """Result of routing operation."""
    matched: bool
    route_match: Optional[RouteMatch]
    fallback_agent: Optional[str] = None
    error: Optional[str] = None
