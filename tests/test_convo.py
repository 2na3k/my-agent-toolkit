"""Tests for conversation agent."""

import pytest
from unittest.mock import patch, MagicMock

# Import agents package to ensure all agents are registered
import src.agents  # noqa: F401

from src.core import AgentFactory
from src.agents.convo import ConvoAgent


class TestConvoAgent:
    """Tests for ConvoAgent."""

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_initialization_with_router(self, mock_client, mock_logger):
        """Test ConvoAgent initialization with router enabled."""
        mock_client_instance = MagicMock()
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"
        mock_client.return_value = mock_client_instance

        agent = ConvoAgent(provider="claude", use_router=True)

        assert agent.name == "ConvoAgent"
        assert agent.use_router is True
        assert agent.router is not None
        assert agent.router_confidence_threshold == 0.7

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_initialization_without_router(self, mock_client, mock_logger):
        """Test ConvoAgent initialization with router disabled."""
        mock_client_instance = MagicMock()
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"
        mock_client.return_value = mock_client_instance

        agent = ConvoAgent(provider="claude", use_router=False)

        assert agent.name == "ConvoAgent"
        assert agent.use_router is False
        assert agent.router is None

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_custom_confidence_threshold(self, mock_client, mock_logger):
        """Test ConvoAgent with custom confidence threshold."""
        mock_client_instance = MagicMock()
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"
        mock_client.return_value = mock_client_instance

        agent = ConvoAgent(provider="claude", router_confidence_threshold=0.9)

        assert agent.router_confidence_threshold == 0.9

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_run_routes_to_specialized_agent(self, mock_client, mock_logger):
        """Test that ConvoAgent routes to specialized agent when confidence is high."""
        mock_client_instance = MagicMock()
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"
        mock_client.return_value = mock_client_instance

        with patch.object(AgentFactory, "get_routable_agents") as mock_agents:
            mock_agents.return_value = {
                "hello_agent": {
                    "patterns": [r"^hello"],
                    "keywords": ["hello"],
                    "priority": 0,
                    "enabled": True,
                }
            }

            agent = ConvoAgent(provider="claude", use_router=True)
            result = agent.run("hello world")

            assert result == "hello"

            # Check routing info was stored
            last_route = agent.get_state("last_route")
            assert last_route is not None
            assert last_route["agent"] == "hello_agent"
            assert last_route["confidence"] >= 0.7

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_run_uses_llm_for_low_confidence(self, mock_client, mock_logger):
        """Test that ConvoAgent uses LLM when route confidence is low."""
        mock_client_instance = MagicMock()
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"

        # Mock chat completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "I'm here to help!"
        mock_client_instance.chat_completion.return_value = mock_response

        mock_client.return_value = mock_client_instance

        with patch.object(AgentFactory, "get_routable_agents") as mock_agents:
            # No matching agents - will fall back to LLM
            mock_agents.return_value = {
                "hello_agent": {
                    "patterns": [r"^hello"],
                    "keywords": ["hello"],
                    "priority": 0,
                    "enabled": True,
                }
            }

            agent = ConvoAgent(provider="claude", use_router=True)
            result = agent.run("tell me about yourself")

            assert result == "I'm here to help!"

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_run_without_router(self, mock_client, mock_logger):
        """Test that ConvoAgent uses LLM directly when router is disabled."""
        mock_client_instance = MagicMock()
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"

        # Mock chat completion response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello! How can I assist you?"
        mock_client_instance.chat_completion.return_value = mock_response

        mock_client.return_value = mock_client_instance

        agent = ConvoAgent(provider="claude", use_router=False)
        result = agent.run("hello")

        assert result == "Hello! How can I assist you?"

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_get_conversation_context(self, mock_client, mock_logger):
        """Test getting conversation context."""
        mock_client_instance = MagicMock()
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"
        mock_client.return_value = mock_client_instance

        agent = ConvoAgent(provider="claude", use_router=True)

        context = agent.get_conversation_context()

        assert "history_length" in context
        assert "last_input" in context
        assert "last_route" in context
        assert "provider" in context
        assert "model" in context
        assert "router_enabled" in context
        assert context["router_enabled"] is True

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_reset_conversation(self, mock_client, mock_logger):
        """Test resetting conversation."""
        mock_client_instance = MagicMock()
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"
        mock_client.return_value = mock_client_instance

        agent = ConvoAgent(provider="claude", use_router=False)

        # Add some state
        agent.set_state("test_key", "test_value")
        agent.history.append({"user": "test", "assistant": "response"})

        # Reset
        agent.reset_conversation()

        assert len(agent.history) == 0
        assert agent.get_state("test_key") is None

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_registered_with_factory(self, mock_client, mock_logger):
        """Test that ConvoAgent is registered with factory."""
        assert AgentFactory.is_registered("convo")

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_disabled_for_routing(self, mock_client, mock_logger):
        """Test that ConvoAgent is disabled for routing (enabled=False)."""
        metadata = AgentFactory.get_metadata("convo")

        assert metadata.get("enabled") is False

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_routing_with_fallback(self, mock_client, mock_logger):
        """Test that ConvoAgent uses LLM when router returns fallback."""
        mock_client_instance = MagicMock()
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"

        # Mock chat completion response for LLM fallback
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "I can help with that."
        mock_client_instance.chat_completion.return_value = mock_response

        mock_client.return_value = mock_client_instance

        with patch.object(AgentFactory, "get_routable_agents") as mock_agents:
            # Empty agents - will trigger fallback
            mock_agents.return_value = {}

            agent = ConvoAgent(provider="claude", use_router=True)
            result = agent.run("random question")

            assert result == "I can help with that."

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_handles_router_failure_gracefully(self, mock_client, mock_logger):
        """Test that ConvoAgent handles router failure gracefully."""
        mock_client_instance = MagicMock()
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"

        # Mock chat completion response for LLM fallback
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Fallback response"
        mock_client_instance.chat_completion.return_value = mock_response

        mock_client.return_value = mock_client_instance

        agent = ConvoAgent(provider="claude", use_router=True)

        # Mock router to raise exception
        agent.router.route = MagicMock(side_effect=Exception("Router error"))

        # Should fall back to LLM gracefully
        result = agent.run("test input")

        assert result == "Fallback response"

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_conversation_history_maintained(self, mock_client, mock_logger):
        """Test that conversation history is maintained across interactions."""
        mock_client_instance = MagicMock()
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"

        # Mock chat completion responses
        mock_response1 = MagicMock()
        mock_response1.choices = [MagicMock()]
        mock_response1.choices[0].message.content = "Response 1"

        mock_response2 = MagicMock()
        mock_response2.choices = [MagicMock()]
        mock_response2.choices[0].message.content = "Response 2"

        mock_client_instance.chat_completion.side_effect = [mock_response1, mock_response2]
        mock_client.return_value = mock_client_instance

        agent = ConvoAgent(provider="claude", use_router=False)

        # First interaction
        agent.run("hello")
        assert len(agent.history) == 1

        # Second interaction
        agent.run("how are you?")
        assert len(agent.history) == 2

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_create_via_factory(self, mock_client, mock_logger):
        """Test creating ConvoAgent via AgentFactory."""
        mock_client_instance = MagicMock()
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"
        mock_client.return_value = mock_client_instance

        agent = AgentFactory.create("convo", provider="claude")

        assert isinstance(agent, ConvoAgent)
        assert agent.name == "convo"
