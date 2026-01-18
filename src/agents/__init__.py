"""Agents package - imports all agents to ensure registration."""

# Import all agents to trigger their @register_agent decorators
from .hello_agent.agent import HelloAgent
from .router.agent import RouterAgent
from .convo.agent import ConvoAgent

__all__ = [
    "HelloAgent",
    "RouterAgent",
    "ConvoAgent",
]
