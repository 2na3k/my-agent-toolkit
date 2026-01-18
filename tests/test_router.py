"""Tests for router agent and routing functionality."""

import pytest
from unittest.mock import patch, MagicMock

# Import agents package to ensure all agents are registered
import src.agents  # noqa: F401

from src.core import AgentFactory
from src.agents.router import RouterAgent, RouteMatch, RouteResult, RoutingEngine, RouteExecutor
from src.agents.router.strategies.metadata import MetadataBasedStrategy


class TestRouteModels:
    """Tests for routing data models."""

    def test_route_match_creation(self):
        """Test RouteMatch creation."""
        match = RouteMatch(
            agent_type="hello_agent",
            confidence=0.95,
            metadata={"matched_pattern": r"hello"},
            strategy_name="metadata"
        )

        assert match.agent_type == "hello_agent"
        assert match.confidence == 0.95
        assert match.metadata["matched_pattern"] == r"hello"
        assert match.strategy_name == "metadata"

    def test_route_result_creation(self):
        """Test RouteResult creation."""
        match = RouteMatch(
            agent_type="hello_agent",
            confidence=0.95,
            metadata={},
            strategy_name="metadata"
        )
        result = RouteResult(matched=True, route_match=match)

        assert result.matched is True
        assert result.route_match == match
        assert result.fallback_agent is None
        assert result.error is None


class TestMetadataBasedStrategy:
    """Tests for metadata-based routing strategy."""

    def test_pattern_matching(self):
        """Test pattern matching in metadata strategy."""
        strategy = MetadataBasedStrategy()

        # Create a mock agent with patterns
        with patch.object(AgentFactory, 'get_routable_agents') as mock_agents:
            mock_agents.return_value = {
                'hello_agent': {
                    'patterns': [r'^hello', r'^hi\b'],
                    'keywords': ['hello', 'hi'],
                    'priority': 0,
                    'enabled': True
                }
            }

            # Test matching input
            match = strategy.match("hello world", {})

            assert match.agent_type == "hello_agent"
            assert match.confidence == 1.0
            assert match.metadata['match_type'] == 'pattern'

    def test_keyword_matching(self):
        """Test keyword matching in metadata strategy."""
        strategy = MetadataBasedStrategy()

        with patch.object(AgentFactory, 'get_routable_agents') as mock_agents:
            mock_agents.return_value = {
                'hello_agent': {
                    'patterns': [],
                    'keywords': ['hello', 'greeting'],
                    'priority': 0,
                    'enabled': True
                }
            }

            # Test matching input
            match = strategy.match("send a greeting", {})

            assert match.agent_type == "hello_agent"
            assert match.confidence > 0
            assert match.metadata['match_type'] == 'keyword'
            assert 'greeting' in match.metadata['matched_keywords']

    def test_no_match(self):
        """Test when no agent matches."""
        strategy = MetadataBasedStrategy()

        with patch.object(AgentFactory, 'get_routable_agents') as mock_agents:
            mock_agents.return_value = {
                'hello_agent': {
                    'patterns': [r'^hello'],
                    'keywords': ['hello'],
                    'priority': 0,
                    'enabled': True
                }
            }

            # Test non-matching input
            match = strategy.match("unrelated input", {})

            assert match.agent_type is None
            assert match.confidence == 0.0

    def test_priority_ordering(self):
        """Test that higher priority agents are checked first."""
        strategy = MetadataBasedStrategy()

        with patch.object(AgentFactory, 'get_routable_agents') as mock_agents:
            mock_agents.return_value = {
                'low_priority': {
                    'patterns': [r'.*'],
                    'keywords': [],
                    'priority': 0,
                    'enabled': True
                },
                'high_priority': {
                    'patterns': [r'.*'],
                    'keywords': [],
                    'priority': 10,
                    'enabled': True
                }
            }

            # Both match, but high priority should win
            match = strategy.match("anything", {})

            assert match.agent_type == "high_priority"


class TestRoutingEngine:
    """Tests for routing engine."""

    def test_engine_initialization(self):
        """Test routing engine initialization."""
        engine = RoutingEngine(default_agent="hello_agent", confidence_threshold=0.6)

        assert engine.default_agent == "hello_agent"
        assert engine.confidence_threshold == 0.6
        assert 'metadata' in engine.strategies

    def test_successful_routing(self):
        """Test successful routing with high confidence."""
        engine = RoutingEngine()

        with patch.object(AgentFactory, 'get_routable_agents') as mock_agents:
            mock_agents.return_value = {
                'hello_agent': {
                    'patterns': [r'^hello'],
                    'keywords': ['hello'],
                    'priority': 0,
                    'enabled': True
                }
            }

            result = engine.route("hello world", {})

            assert result.matched is True
            assert result.route_match.agent_type == "hello_agent"
            assert result.route_match.confidence >= engine.confidence_threshold

    def test_fallback_to_default(self):
        """Test fallback to default agent when no match."""
        engine = RoutingEngine(default_agent="hello_agent")

        with patch.object(AgentFactory, 'get_routable_agents') as mock_agents:
            mock_agents.return_value = {
                'hello_agent': {
                    'patterns': [r'^hello'],
                    'keywords': ['hello'],
                    'priority': 0,
                    'enabled': True
                }
            }

            result = engine.route("unrelated input", {})

            assert result.matched is True
            assert result.fallback_agent == "hello_agent"
            assert result.route_match.agent_type == "hello_agent"

    def test_add_strategy(self):
        """Test adding a new routing strategy."""
        engine = RoutingEngine()

        mock_strategy = MagicMock()
        engine.add_strategy("custom", mock_strategy)

        assert "custom" in engine.strategies


class TestRouteExecutor:
    """Tests for route executor."""

    @patch('src.core.agent.get_logger')
    @patch('src.core.agent.AIClientWrapper')
    def test_execute_successful(self, mock_client, mock_logger):
        """Test successful agent execution."""
        executor = RouteExecutor()

        # Create a route result
        match = RouteMatch(
            agent_type="hello_agent",
            confidence=0.95,
            metadata={},
            strategy_name="metadata"
        )
        result = RouteResult(matched=True, route_match=match)

        # Mock the client
        mock_client_instance = MagicMock()
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"
        mock_client.return_value = mock_client_instance

        # Execute
        output = executor.execute(result, "hello", provider="claude")

        assert output == "hello"

    def test_execute_unmatched_route(self):
        """Test execution with unmatched route raises error."""
        executor = RouteExecutor()

        result = RouteResult(matched=False, route_match=None, error="No match")

        with pytest.raises(ValueError, match="Cannot execute unmatched route"):
            executor.execute(result, "hello")


class TestRouterAgent:
    """Tests for RouterAgent."""

    @patch('src.core.agent.get_logger')
    @patch('src.core.agent.AIClientWrapper')
    def test_router_initialization(self, mock_client, mock_logger):
        """Test RouterAgent initialization."""
        mock_client_instance = MagicMock()
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"
        mock_client.return_value = mock_client_instance

        router = RouterAgent(
            provider="claude",
            default_agent="hello_agent",
            confidence_threshold=0.6
        )

        assert router.name == "RouterAgent"
        assert router.engine.default_agent == "hello_agent"
        assert router.engine.confidence_threshold == 0.6

    @patch('src.core.agent.get_logger')
    @patch('src.core.agent.AIClientWrapper')
    def test_router_run(self, mock_client, mock_logger):
        """Test RouterAgent run method."""
        mock_client_instance = MagicMock()
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"
        mock_client.return_value = mock_client_instance

        with patch.object(AgentFactory, 'get_routable_agents') as mock_agents:
            mock_agents.return_value = {
                'hello_agent': {
                    'patterns': [r'.*'],
                    'keywords': ['hello'],
                    'priority': 0,
                    'enabled': True
                }
            }

            router = RouterAgent(provider="claude")
            result = router.run("hello world")

            assert result == "hello"

    @patch('src.core.agent.get_logger')
    @patch('src.core.agent.AIClientWrapper')
    def test_router_get_routing_stats(self, mock_client, mock_logger):
        """Test getting routing statistics."""
        mock_client_instance = MagicMock()
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"
        mock_client.return_value = mock_client_instance

        with patch.object(AgentFactory, 'get_routable_agents') as mock_agents:
            mock_agents.return_value = {
                'hello_agent': {
                    'patterns': [r'.*'],
                    'keywords': ['hello'],
                    'priority': 0,
                    'enabled': True
                }
            }

            router = RouterAgent(provider="claude")
            router.run("hello")

            stats = router.get_routing_stats()

            assert 'last_route' in stats
            assert 'available_strategies' in stats
            assert 'default_agent' in stats
            assert stats['last_route']['agent'] == 'hello_agent'

    @patch('src.core.agent.get_logger')
    @patch('src.core.agent.AIClientWrapper')
    def test_router_registered_with_factory(self, mock_client, mock_logger):
        """Test that RouterAgent is registered with factory."""
        assert AgentFactory.is_registered("router")

    @patch('src.core.agent.get_logger')
    @patch('src.core.agent.AIClientWrapper')
    def test_router_disabled_for_routing(self, mock_client, mock_logger):
        """Test that RouterAgent is disabled for routing (enabled=False)."""
        metadata = AgentFactory.get_metadata("router")

        assert metadata.get('enabled') is False


class TestAgentFactoryMetadata:
    """Tests for AgentFactory metadata functionality."""

    def test_get_metadata(self):
        """Test getting metadata for an agent."""
        metadata = AgentFactory.get_metadata("hello_agent")

        assert 'patterns' in metadata
        assert 'keywords' in metadata
        assert 'description' in metadata
        assert 'priority' in metadata

    def test_get_all_metadata(self):
        """Test getting all agent metadata."""
        all_metadata = AgentFactory.get_all_metadata()

        assert 'hello_agent' in all_metadata
        assert 'router' in all_metadata

    def test_get_routable_agents(self):
        """Test getting only routable agents (enabled=True)."""
        routable = AgentFactory.get_routable_agents()

        # hello_agent should be routable
        assert 'hello_agent' in routable

        # router should NOT be routable (enabled=False)
        assert 'router' not in routable
