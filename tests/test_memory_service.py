"""Tests for MemoryService."""

import tempfile
from pathlib import Path

import pytest

from src.core.db import DatabaseManager
from src.core.memory import MemoryService


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


class TestMemoryServiceCreation:
    """Test MemoryService initialization and conversation creation."""

    def test_create_service(self, temp_db):
        """Test creating MemoryService."""
        service = MemoryService(temp_db)
        assert service.db is temp_db

    def test_create_conversation(self, memory_service):
        """Test creating a new conversation."""
        conv_id = memory_service.create_conversation(
            agent_type="convo",
            provider="claude",
            model="claude-3-5-sonnet-20241022",
            metadata={"source": "test"},
        )

        assert conv_id is not None
        assert len(conv_id) == 36  # UUID format

        # Verify conversation was created
        conversation = memory_service.db.get_conversation(conv_id)
        assert conversation is not None
        assert conversation["agent_type"] == "convo"
        assert conversation["provider"] == "claude"

    def test_create_conversation_minimal(self, memory_service):
        """Test creating conversation with minimal parameters."""
        conv_id = memory_service.create_conversation(agent_type="convo")

        assert conv_id is not None
        conversation = memory_service.db.get_conversation(conv_id)
        assert conversation["agent_type"] == "convo"
        assert conversation["provider"] is None
        assert conversation["model"] is None


class TestConversationLoading:
    """Test loading conversations."""

    def test_load_conversation(self, memory_service):
        """Test loading conversation with messages."""
        conv_id = memory_service.create_conversation(agent_type="convo")

        # Add some messages
        memory_service.db.add_message(conv_id, "user", "Hello")
        memory_service.db.add_message(conv_id, "assistant", "Hi there!")

        # Load conversation
        data = memory_service.load_conversation(conv_id)

        assert data is not None
        assert "conversation" in data
        assert "messages" in data
        assert len(data["messages"]) == 2

    def test_load_nonexistent_conversation(self, memory_service):
        """Test loading conversation that doesn't exist."""
        data = memory_service.load_conversation("nonexistent-id")
        assert data is None


class TestTurnSaving:
    """Test saving conversation turns."""

    def test_save_turn(self, memory_service):
        """Test saving a conversation turn."""
        conv_id = memory_service.create_conversation(agent_type="convo")

        memory_service.save_turn(
            conversation_id=conv_id,
            user_message="What is Python?",
            assistant_message="Python is a programming language.",
        )

        # Verify messages were saved
        messages = memory_service.db.get_messages(conv_id)
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "What is Python?"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Python is a programming language."

    def test_save_turn_with_metadata(self, memory_service):
        """Test saving turn with metadata."""
        conv_id = memory_service.create_conversation(agent_type="convo")

        memory_service.save_turn(
            conversation_id=conv_id,
            user_message="Hello",
            assistant_message="Hi",
            metadata={"source": "cli"},
        )

        messages = memory_service.db.get_messages(conv_id)
        assert messages[0]["metadata"] == {"source": "cli"}
        assert messages[1]["metadata"] == {"source": "cli"}

    def test_auto_title_generation(self, memory_service):
        """Test auto-title generation on first turn."""
        conv_id = memory_service.create_conversation(agent_type="convo")

        # First turn should generate title
        memory_service.save_turn(
            conversation_id=conv_id,
            user_message="Tell me about quantum computing",
            assistant_message="Sure, quantum computing is...",
        )

        conversation = memory_service.db.get_conversation(conv_id)
        assert conversation["title"] is not None
        assert "quantum computing" in conversation["title"].lower()

    def test_title_not_regenerated_on_second_turn(self, memory_service):
        """Test title is not regenerated on subsequent turns."""
        conv_id = memory_service.create_conversation(agent_type="convo")

        # First turn
        memory_service.save_turn(
            conversation_id=conv_id,
            user_message="First message",
            assistant_message="Response",
        )

        conversation = memory_service.db.get_conversation(conv_id)
        first_title = conversation["title"]

        # Second turn
        memory_service.save_turn(
            conversation_id=conv_id,
            user_message="Second message",
            assistant_message="Response",
        )

        conversation = memory_service.db.get_conversation(conv_id)
        assert conversation["title"] == first_title  # Should not change

    def test_title_truncation(self, memory_service):
        """Test long titles are truncated."""
        conv_id = memory_service.create_conversation(agent_type="convo")

        long_message = "This is a very long message that exceeds fifty characters and should be truncated by the auto-title generator"

        memory_service.save_turn(
            conversation_id=conv_id,
            user_message=long_message,
            assistant_message="Response",
        )

        conversation = memory_service.db.get_conversation(conv_id)
        assert len(conversation["title"]) == 50
        assert conversation["title"].endswith("...")


class TestHistoryRetrieval:
    """Test conversation history retrieval."""

    def test_get_history_for_context(self, memory_service):
        """Test getting formatted history for LLM context."""
        conv_id = memory_service.create_conversation(agent_type="convo")

        # Add multiple turns
        for i in range(5):
            memory_service.save_turn(
                conversation_id=conv_id,
                user_message=f"User message {i}",
                assistant_message=f"Assistant response {i}",
            )

        # Get recent history
        history = memory_service.get_history_for_context(conv_id, max_messages=6)

        # Should get last 3 turns (6 messages)
        assert len(history) == 6
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "User message 2"
        assert history[1]["role"] == "assistant"
        assert "role" in history[0]
        assert "content" in history[0]

    def test_get_history_formatted_correctly(self, memory_service):
        """Test history is formatted with role and content only."""
        conv_id = memory_service.create_conversation(agent_type="convo")

        memory_service.save_turn(
            conversation_id=conv_id,
            user_message="Hello",
            assistant_message="Hi",
        )

        history = memory_service.get_history_for_context(conv_id)

        # Should only have role and content keys
        assert set(history[0].keys()) == {"role", "content"}
        assert set(history[1].keys()) == {"role", "content"}


class TestStateManagement:
    """Test agent state management."""

    def test_save_state(self, memory_service):
        """Test saving agent state."""
        conv_id = memory_service.create_conversation(agent_type="convo")

        state = {
            "counter": 42,
            "name": "Alice",
            "settings": {"theme": "dark"},
        }

        memory_service.save_state(conv_id, state)

        # Verify state was saved
        loaded_state = memory_service.load_state(conv_id)
        assert loaded_state == state

    def test_load_empty_state(self, memory_service):
        """Test loading state when none exists."""
        conv_id = memory_service.create_conversation(agent_type="convo")

        state = memory_service.load_state(conv_id)
        assert state == {}


class TestConversationListing:
    """Test listing conversations."""

    def test_list_recent_conversations(self, memory_service):
        """Test listing recent conversations."""
        # Create multiple conversations
        conv1 = memory_service.create_conversation(agent_type="convo")
        conv2 = memory_service.create_conversation(agent_type="convo")
        conv3 = memory_service.create_conversation(agent_type="hello_agent")

        # List all conversations
        conversations = memory_service.list_recent_conversations()
        assert len(conversations) >= 3

    def test_list_conversations_by_agent_type(self, memory_service):
        """Test filtering conversations by agent type."""
        conv1 = memory_service.create_conversation(agent_type="convo")
        conv2 = memory_service.create_conversation(agent_type="hello_agent")

        # List only convo conversations
        convo_conversations = memory_service.list_recent_conversations(agent_type="convo")
        assert len(convo_conversations) >= 1
        assert all(c["agent_type"] == "convo" for c in convo_conversations)

    def test_list_conversations_with_limit(self, memory_service):
        """Test limiting number of conversations returned."""
        for i in range(5):
            memory_service.create_conversation(agent_type="convo")

        conversations = memory_service.list_recent_conversations(limit=3)
        assert len(conversations) == 3


class TestConversationManagement:
    """Test conversation management operations."""

    def test_set_conversation_title(self, memory_service):
        """Test manually setting conversation title."""
        conv_id = memory_service.create_conversation(agent_type="convo")

        memory_service.set_conversation_title(conv_id, "Custom Title")

        conversation = memory_service.db.get_conversation(conv_id)
        assert conversation["title"] == "Custom Title"

    def test_delete_conversation(self, memory_service):
        """Test deleting conversation."""
        conv_id = memory_service.create_conversation(agent_type="convo")

        # Add some data
        memory_service.save_turn(conv_id, "Hello", "Hi")
        memory_service.save_state(conv_id, {"key": "value"})

        # Delete conversation
        memory_service.delete_conversation(conv_id)

        # Verify it's gone
        conversation = memory_service.db.get_conversation(conv_id)
        assert conversation is None

        # Verify related data is also gone
        messages = memory_service.db.get_messages(conv_id)
        assert len(messages) == 0

        state = memory_service.load_state(conv_id)
        assert len(state) == 0
