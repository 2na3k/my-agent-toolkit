import pytest
from unittest.mock import Mock, patch

from src.agents.hello_agent import HelloAgent
from src.core import AgentFactory


class TestHelloAgent:
    """Test suite for HelloAgent."""

    @patch('src.core.agent.get_logger')
    @patch('src.core.agent.AIClientWrapper')
    def test_init(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test HelloAgent initialization."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = 'claude'
        mock_client.get_default_model.return_value = 'claude-sonnet-4-5'
        mock_client_class.return_value = mock_client

        agent = HelloAgent()

        assert agent.name == "HelloAgent"
        assert isinstance(agent, HelloAgent)

    @patch('src.core.agent.get_logger')
    @patch('src.core.agent.AIClientWrapper')
    def test_init_custom_name(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test HelloAgent initialization with custom name."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = 'claude'
        mock_client.get_default_model.return_value = 'claude-sonnet-4-5'
        mock_client_class.return_value = mock_client

        agent = HelloAgent(name="CustomHello")

        assert agent.name == "CustomHello"

    @patch('src.core.agent.get_logger')
    @patch('src.core.agent.AIClientWrapper')
    def test_run_returns_hello(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test that run always returns 'hello'."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = 'claude'
        mock_client.get_default_model.return_value = 'claude-sonnet-4-5'
        mock_client_class.return_value = mock_client

        agent = HelloAgent()

        # Test with different inputs
        assert agent.run("anything") == "hello"
        assert agent.run("") == "hello"
        assert agent.run(None) == "hello"
        assert agent.run(123) == "hello"
        assert agent.run({"key": "value"}) == "hello"
        assert agent.run([1, 2, 3]) == "hello"

    @patch('src.core.agent.get_logger')
    @patch('src.core.agent.AIClientWrapper')
    def test_run_stores_input_in_state(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test that run stores input in agent state."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = 'claude'
        mock_client.get_default_model.return_value = 'claude-sonnet-4-5'
        mock_client_class.return_value = mock_client

        agent = HelloAgent()

        agent.run("test input")

        assert agent.get_state("last_input") == "test input"

    @patch('src.core.agent.get_logger')
    @patch('src.core.agent.AIClientWrapper')
    def test_greet_without_name(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test greet method without a name."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = 'claude'
        mock_client.get_default_model.return_value = 'claude-sonnet-4-5'
        mock_client_class.return_value = mock_client

        agent = HelloAgent()

        assert agent.greet() == "hello"

    @patch('src.core.agent.get_logger')
    @patch('src.core.agent.AIClientWrapper')
    def test_greet_with_name(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test greet method with a name."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = 'claude'
        mock_client.get_default_model.return_value = 'claude-sonnet-4-5'
        mock_client_class.return_value = mock_client

        agent = HelloAgent()

        assert agent.greet("World") == "hello, World!"
        assert agent.greet("Alice") == "hello, Alice!"
        assert agent.greet("Bob") == "hello, Bob!"

    @patch('src.core.agent.get_logger')
    @patch('src.core.agent.AIClientWrapper')
    def test_multiple_runs(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test multiple runs update state correctly."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = 'claude'
        mock_client.get_default_model.return_value = 'claude-sonnet-4-5'
        mock_client_class.return_value = mock_client

        agent = HelloAgent()

        agent.run("first input")
        assert agent.get_state("last_input") == "first input"

        agent.run("second input")
        assert agent.get_state("last_input") == "second input"

        agent.run("third input")
        assert agent.get_state("last_input") == "third input"

    @patch('src.core.agent.get_logger')
    @patch('src.core.agent.AIClientWrapper')
    def test_registered_with_factory(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test that HelloAgent is registered with AgentFactory."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = 'claude'
        mock_client.get_default_model.return_value = 'claude-sonnet-4-5'
        mock_client_class.return_value = mock_client

        # Check if registered
        assert AgentFactory.is_registered("hello_agent")

        # Create via factory
        agent = AgentFactory.create("hello_agent")

        assert isinstance(agent, HelloAgent)
        assert agent.run("test") == "hello"

    @patch('src.core.agent.get_logger')
    @patch('src.core.agent.AIClientWrapper')
    def test_inherits_base_agent_features(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test that HelloAgent inherits all BaseAgent features."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = 'claude'
        mock_client.get_default_model.return_value = 'claude-sonnet-4-5'
        mock_client_class.return_value = mock_client

        agent = HelloAgent()

        # Test state management
        agent.set_state("test_key", "test_value")
        assert agent.get_state("test_key") == "test_value"

        # Test state reset
        agent.reset_state()
        assert agent.get_state("test_key") is None

        # Test history (should be empty since we don't use chat)
        assert agent.history == []

    @patch('src.core.agent.get_logger')
    @patch('src.core.agent.AIClientWrapper')
    def test_run_with_kwargs(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test run method accepts and ignores kwargs."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = 'claude'
        mock_client.get_default_model.return_value = 'claude-sonnet-4-5'
        mock_client_class.return_value = mock_client

        agent = HelloAgent()

        # Should work with extra kwargs
        result = agent.run(
            "input",
            extra_param1="value1",
            extra_param2="value2",
            temperature=0.5
        )

        assert result == "hello"

    @patch('src.core.agent.get_logger')
    @patch('src.core.agent.AIClientWrapper')
    def test_logger_calls(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test that logger is used correctly."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_client = Mock()
        mock_client.current_provider = 'claude'
        mock_client.get_default_model.return_value = 'claude-sonnet-4-5'
        mock_client_class.return_value = mock_client

        agent = HelloAgent()
        agent.run("test input")

        # Verify logger was called
        assert mock_logger.info.called
        assert mock_logger.debug.called
