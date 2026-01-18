import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Any

from src.core.agent import BaseAgent, AgentFactory, register_agent


# Sample concrete agent for testing
class SampleAgent(BaseAgent):
    """Test agent implementation."""

    def run(self, input_data: Any, **kwargs) -> str:
        """Simple run implementation for testing."""
        return f"Processed: {input_data}"


class TestBaseAgent:
    """Test suite for BaseAgent class."""

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_init_success(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test successful agent initialization."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"
        mock_client_class.return_value = mock_client

        agent = SampleAgent(name="test_agent", provider="claude")

        assert agent.name == "test_agent"
        assert agent.provider == "claude"
        assert agent.state == {}
        assert agent.history == []
        mock_get_logger.assert_called_once_with("agent.test_agent")

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_init_with_model(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test initialization with specific model."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = "openai"
        mock_client.get_default_model.return_value = "gpt-4o"
        mock_client_class.return_value = mock_client

        agent = SampleAgent(name="test_agent", provider="openai", model="gpt-4o")

        assert agent.model == "gpt-4o"

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_init_client_failure(self, mock_client_class, mock_get_logger):
        """Test initialization when client creation fails."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client_class.side_effect = Exception("Client creation failed")

        with pytest.raises(Exception, match="Client creation failed"):
            SampleAgent(name="test_agent")

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_chat_simple(
        self, mock_client_class, mock_get_logger, mock_env_vars, mock_openai_response
    ):
        """Test simple chat without history."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"
        mock_client.chat_completion.return_value = mock_openai_response
        mock_client_class.return_value = mock_client

        agent = SampleAgent(name="test_agent")
        response = agent.chat("Hello")

        mock_client.chat_completion.assert_called_once()
        call_args = mock_client.chat_completion.call_args
        assert call_args[1]["messages"] == [{"role": "user", "content": "Hello"}]

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_chat_with_parameters(
        self, mock_client_class, mock_get_logger, mock_env_vars, mock_openai_response
    ):
        """Test chat with custom parameters."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"
        mock_client.chat_completion.return_value = mock_openai_response
        mock_client_class.return_value = mock_client

        agent = SampleAgent(name="test_agent")
        response = agent.chat("Hello", temperature=0.5, max_tokens=1000, stream=True)

        call_args = mock_client.chat_completion.call_args[1]
        assert call_args["temperature"] == 0.5
        assert call_args["max_tokens"] == 1000
        assert call_args["stream"] is True

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_chat_updates_history(
        self, mock_client_class, mock_get_logger, mock_env_vars
    ):
        """Test that chat updates conversation history."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"

        # Create mock response
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "AI response"
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat_completion.return_value = mock_response
        mock_client_class.return_value = mock_client

        agent = SampleAgent(name="test_agent")
        agent.chat("Hello")

        assert len(agent.history) == 1
        assert agent.history[0]["user"] == "Hello"
        assert agent.history[0]["assistant"] == "AI response"

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_chat_with_history(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test chat includes conversation history."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "Response"
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat_completion.return_value = mock_response
        mock_client_class.return_value = mock_client

        agent = SampleAgent(name="test_agent")

        # First message
        agent.chat("First message")

        # Second message should include history
        agent.chat("Second message")

        # Check that second call includes history
        second_call_args = mock_client.chat_completion.call_args[1]
        messages = second_call_args["messages"]

        assert len(messages) == 3  # user1, assistant1, user2
        assert messages[0]["content"] == "First message"
        assert messages[1]["content"] == "Response"
        assert messages[2]["content"] == "Second message"

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_clear_history(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test clearing conversation history."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"
        mock_client_class.return_value = mock_client

        agent = SampleAgent(name="test_agent")
        agent.history = [{"user": "test", "assistant": "response"}]

        agent.clear_history()

        assert len(agent.history) == 0

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_state_management(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test state management methods."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"
        mock_client_class.return_value = mock_client

        agent = SampleAgent(name="test_agent")

        # Set state
        agent.set_state("key1", "value1")
        agent.set_state("key2", 42)

        # Get state
        assert agent.get_state("key1") == "value1"
        assert agent.get_state("key2") == 42
        assert agent.get_state("nonexistent") is None
        assert agent.get_state("nonexistent", "default") == "default"

        # Reset state
        agent.reset_state()
        assert agent.state == {}

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_switch_provider(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test switching providers."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"
        mock_client_class.return_value = mock_client

        agent = SampleAgent(name="test_agent", provider="claude")

        agent.switch_provider("openai")

        mock_client.switch_provider.assert_called_once_with("openai")
        assert agent.provider == "openai"

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_switch_model(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test switching models."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"
        mock_client_class.return_value = mock_client

        agent = SampleAgent(name="test_agent")
        agent.switch_model("gpt-4o")

        assert agent.model == "gpt-4o"

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_run_method(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test run method implementation."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"
        mock_client_class.return_value = mock_client

        agent = SampleAgent(name="test_agent")
        result = agent.run("test input")

        assert result == "Processed: test input"

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_repr(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test string representation."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"
        mock_client_class.return_value = mock_client

        agent = SampleAgent(name="test_agent")
        repr_str = repr(agent)

        assert "SampleAgent" in repr_str
        assert "test_agent" in repr_str


class SampleAgentFactory:
    """Test suite for AgentFactory class."""

    def setup_method(self):
        """Clear registered agents before each test."""
        AgentFactory._registered_agents.clear()

    def test_register_agent(self):
        """Test registering an agent class."""
        AgentFactory.register("test_agent", SampleAgent)

        assert AgentFactory.is_registered("test_agent")
        assert "test_agent" in AgentFactory.list_agents()

    def test_register_invalid_class(self):
        """Test registering a class that doesn't inherit from BaseAgent."""

        class InvalidAgent:
            pass

        with pytest.raises(TypeError, match="must inherit from BaseAgent"):
            AgentFactory.register("invalid", InvalidAgent)

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_create_agent(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test creating an agent instance."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"
        mock_client_class.return_value = mock_client

        AgentFactory.register("test_agent", SampleAgent)
        agent = AgentFactory.create("test_agent", name="my_agent")

        assert isinstance(agent, SampleAgent)
        assert agent.name == "my_agent"

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_create_agent_default_name(
        self, mock_client_class, mock_get_logger, mock_env_vars
    ):
        """Test creating agent with default name."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"
        mock_client_class.return_value = mock_client

        AgentFactory.register("test_agent", SampleAgent)
        agent = AgentFactory.create("test_agent")

        assert agent.name == "test_agent"

    def test_create_unregistered_agent(self):
        """Test creating an agent that isn't registered."""
        with pytest.raises(ValueError, match="Agent type 'nonexistent' not registered"):
            AgentFactory.create("nonexistent")

    @patch("src.core.agent.ClientFactory")
    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_create_with_model(
        self, mock_client_class, mock_get_logger, mock_client_factory, mock_env_vars
    ):
        """Test creating agent with model-based provider detection."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"
        mock_client_class.return_value = mock_client

        # Mock ClientFactory
        mock_factory_instance = Mock()
        mock_factory_instance.get_provider_for_model.return_value = "claude"
        mock_client_factory.return_value = mock_factory_instance

        AgentFactory.register("test_agent", SampleAgent)
        agent = AgentFactory.create_with_model("test_agent", "claude-sonnet-4-5")

        assert isinstance(agent, SampleAgent)
        mock_factory_instance.get_provider_for_model.assert_called_once_with(
            "claude-sonnet-4-5"
        )

    @patch("src.core.agent.ClientFactory")
    def test_create_with_invalid_model(self, mock_client_factory):
        """Test creating agent with model that doesn't exist."""
        mock_factory_instance = Mock()
        mock_factory_instance.get_provider_for_model.return_value = None
        mock_client_factory.return_value = mock_factory_instance

        AgentFactory.register("test_agent", SampleAgent)

        with pytest.raises(ValueError, match="Model 'invalid-model' not found"):
            AgentFactory.create_with_model("test_agent", "invalid-model")

    def test_list_agents(self):
        """Test listing registered agents."""
        AgentFactory.register("agent1", SampleAgent)
        AgentFactory.register("agent2", SampleAgent)

        agents = AgentFactory.list_agents()

        assert "agent1" in agents
        assert "agent2" in agents
        assert len(agents) == 2

    def test_unregister_agent(self):
        """Test unregistering an agent."""
        AgentFactory.register("test_agent", SampleAgent)
        assert AgentFactory.is_registered("test_agent")

        AgentFactory.unregister("test_agent")
        assert not AgentFactory.is_registered("test_agent")

    def test_register_decorator(self):
        """Test the register_agent decorator."""

        @register_agent("decorated_agent")
        class DecoratedAgent(BaseAgent):
            def run(self, input_data, **kwargs):
                return input_data

        assert AgentFactory.is_registered("decorated_agent")
        assert AgentFactory._registered_agents["decorated_agent"] == DecoratedAgent
