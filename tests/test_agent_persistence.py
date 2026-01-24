"""Tests for BaseAgent persistence functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.core.agent import AgentFactory, BaseAgent
from src.core.db import DatabaseManager
from src.core.memory import MemoryService


class TestAgent(BaseAgent):
    """Concrete agent for testing."""

    def run(self, input_data, **kwargs):
        return f"Processed: {input_data}"


@pytest.fixture
def temp_db():
    """Create temporary test database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    # Reset singleton for testing
    DatabaseManager._instance = None
    DatabaseManager._initialized = False

    db = DatabaseManager(db_path)
    yield db

    # Cleanup
    db.close()
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def memory_service(temp_db):
    """Create MemoryService with test database."""
    return MemoryService(temp_db)


class TestAgentPersistenceInitialization:
    """Test agent initialization with persistence."""

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_agent_without_persistence(self, mock_client, mock_logger):
        """Test agent works without persistence (backward compatible)."""
        mock_client.return_value.current_provider = "claude"
        mock_client.return_value.get_default_model.return_value = "claude-3-5-sonnet-20241022"

        agent = TestAgent(name="test_agent")

        assert agent.conversation_id is None
        assert agent.memory_service is None
        assert agent.history == []
        assert agent.state == {}

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_agent_with_empty_conversation(self, mock_client, mock_logger, memory_service):
        """Test agent initialization with new conversation."""
        mock_client.return_value.current_provider = "claude"
        mock_client.return_value.get_default_model.return_value = "claude-3-5-sonnet-20241022"

        # Create new conversation
        conv_id = memory_service.create_conversation(agent_type="test")

        # Create agent with persistence
        agent = TestAgent(
            name="test_agent",
            conversation_id=conv_id,
            memory_service=memory_service,
        )

        assert agent.conversation_id == conv_id
        assert agent.memory_service is memory_service
        assert agent.history == []
        assert agent.state == {}

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_agent_loads_existing_conversation(self, mock_client, mock_logger, memory_service):
        """Test agent loads history from existing conversation."""
        mock_client.return_value.current_provider = "claude"
        mock_client.return_value.get_default_model.return_value = "claude-3-5-sonnet-20241022"

        # Create conversation with existing history
        conv_id = memory_service.create_conversation(agent_type="test")
        memory_service.save_turn(conv_id, "Hello", "Hi there!")
        memory_service.save_turn(conv_id, "How are you?", "I'm doing well!")

        # Create agent - should load history
        agent = TestAgent(
            name="test_agent",
            conversation_id=conv_id,
            memory_service=memory_service,
        )

        assert len(agent.history) == 2
        assert agent.history[0]["user"] == "Hello"
        assert agent.history[0]["assistant"] == "Hi there!"
        assert agent.history[1]["user"] == "How are you?"
        assert agent.history[1]["assistant"] == "I'm doing well!"

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_agent_loads_existing_state(self, mock_client, mock_logger, memory_service):
        """Test agent loads state from existing conversation."""
        mock_client.return_value.current_provider = "claude"
        mock_client.return_value.get_default_model.return_value = "claude-3-5-sonnet-20241022"

        # Create conversation with state
        conv_id = memory_service.create_conversation(agent_type="test")
        memory_service.save_state(conv_id, {"counter": 5, "mode": "active"})

        # Create agent - should load state
        agent = TestAgent(
            name="test_agent",
            conversation_id=conv_id,
            memory_service=memory_service,
        )

        assert agent.state == {"counter": 5, "mode": "active"}

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_agent_handles_nonexistent_conversation(self, mock_client, mock_logger, memory_service):
        """Test agent handles nonexistent conversation gracefully."""
        mock_client.return_value.current_provider = "claude"
        mock_client.return_value.get_default_model.return_value = "claude-3-5-sonnet-20241022"

        # Create agent with nonexistent conversation
        agent = TestAgent(
            name="test_agent",
            conversation_id="nonexistent-id",
            memory_service=memory_service,
        )

        # Should initialize with empty history/state rather than crashing
        assert agent.history == []
        assert agent.state == {}


class TestAgentPersistenceOperations:
    """Test agent persistence operations."""

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_chat_persists_messages(self, mock_client, mock_logger, memory_service):
        """Test chat messages are persisted."""
        mock_client.return_value.current_provider = "claude"
        mock_client.return_value.get_default_model.return_value = "claude-3-5-sonnet-20241022"

        # Mock chat completion response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Hello! How can I help?"
        mock_client.return_value.chat_completion.return_value = mock_response

        # Create conversation
        conv_id = memory_service.create_conversation(agent_type="test")

        # Create agent with persistence
        agent = TestAgent(
            name="test_agent",
            conversation_id=conv_id,
            memory_service=memory_service,
        )

        # Send chat message
        agent.chat("What is Python?")

        # Verify message was persisted
        messages = memory_service.db.get_messages(conv_id)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "What is Python?"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Hello! How can I help?"

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_set_state_persists(self, mock_client, mock_logger, memory_service):
        """Test set_state persists to database."""
        mock_client.return_value.current_provider = "claude"
        mock_client.return_value.get_default_model.return_value = "claude-3-5-sonnet-20241022"

        # Create conversation
        conv_id = memory_service.create_conversation(agent_type="test")

        # Create agent with persistence
        agent = TestAgent(
            name="test_agent",
            conversation_id=conv_id,
            memory_service=memory_service,
        )

        # Set state
        agent.set_state("counter", 42)
        agent.set_state("name", "Alice")

        # Verify state was persisted
        persisted_state = memory_service.load_state(conv_id)
        assert persisted_state["counter"] == 42
        assert persisted_state["name"] == "Alice"

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_chat_without_persistence(self, mock_client, mock_logger):
        """Test chat works without persistence (backward compatible)."""
        mock_client.return_value.current_provider = "claude"
        mock_client.return_value.get_default_model.return_value = "claude-3-5-sonnet-20241022"

        # Mock chat completion response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Hello!"
        mock_client.return_value.chat_completion.return_value = mock_response

        # Create agent WITHOUT persistence
        agent = TestAgent(name="test_agent")

        # Chat should work
        response = agent.chat("Hello")
        assert response is not None

        # History updated in memory
        assert len(agent.history) == 1

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_set_state_without_persistence(self, mock_client, mock_logger):
        """Test set_state works without persistence (backward compatible)."""
        mock_client.return_value.current_provider = "claude"
        mock_client.return_value.get_default_model.return_value = "claude-3-5-sonnet-20241022"

        # Create agent WITHOUT persistence
        agent = TestAgent(name="test_agent")

        # Set state should work
        agent.set_state("key", "value")
        assert agent.state["key"] == "value"


class TestAgentFactoryPersistence:
    """Test AgentFactory with persistence parameters."""

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_factory_create_without_persistence(self, mock_client, mock_logger):
        """Test factory creates agent without persistence."""
        mock_client.return_value.current_provider = "claude"
        mock_client.return_value.get_default_model.return_value = "claude-3-5-sonnet-20241022"

        # Register test agent
        AgentFactory.register("test_agent", TestAgent)

        # Create without persistence
        agent = AgentFactory.create("test_agent")

        assert agent.conversation_id is None
        assert agent.memory_service is None

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_factory_create_with_persistence(self, mock_client, mock_logger, memory_service):
        """Test factory creates agent with persistence."""
        mock_client.return_value.current_provider = "claude"
        mock_client.return_value.get_default_model.return_value = "claude-3-5-sonnet-20241022"

        # Register test agent
        AgentFactory.register("test_agent", TestAgent)

        # Create conversation
        conv_id = memory_service.create_conversation(agent_type="test")

        # Create with persistence
        agent = AgentFactory.create(
            "test_agent",
            conversation_id=conv_id,
            memory_service=memory_service,
        )

        assert agent.conversation_id == conv_id
        assert agent.memory_service is memory_service


class TestConversationResumption:
    """Test resuming conversations across agent instances."""

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_resume_conversation_across_instances(self, mock_client, mock_logger, memory_service):
        """Test conversation can be resumed across different agent instances."""
        mock_client.return_value.current_provider = "claude"
        mock_client.return_value.get_default_model.return_value = "claude-3-5-sonnet-20241022"

        # Mock chat completion response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Response"
        mock_client.return_value.chat_completion.return_value = mock_response

        # Create conversation
        conv_id = memory_service.create_conversation(agent_type="test")

        # First agent instance
        agent1 = TestAgent(
            name="agent1",
            conversation_id=conv_id,
            memory_service=memory_service,
        )
        agent1.chat("Message 1")
        agent1.set_state("counter", 1)

        # Simulate closing first agent and creating new one
        agent2 = TestAgent(
            name="agent2",
            conversation_id=conv_id,
            memory_service=memory_service,
        )

        # Second agent should have loaded history and state
        assert len(agent2.history) == 1
        assert agent2.history[0]["user"] == "Message 1"
        assert agent2.state["counter"] == 1

        # Continue conversation with second agent
        agent2.chat("Message 2")

        # Both messages should be persisted
        messages = memory_service.db.get_messages(conv_id)
        assert len(messages) == 4  # 2 turns = 4 messages
