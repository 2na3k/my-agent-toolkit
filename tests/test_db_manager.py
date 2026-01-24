"""Tests for DatabaseManager."""

import json
import tempfile
import threading
import time
from pathlib import Path

import pytest

from src.core.db import DatabaseManager


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


class TestDatabaseInitialization:
    """Test database initialization and schema creation."""

    def test_database_created(self, temp_db):
        """Test database file is created."""
        assert Path(temp_db.db_path).exists()

    def test_singleton_pattern(self, temp_db):
        """Test singleton pattern returns same instance."""
        db2 = DatabaseManager.get_instance()
        assert db2 is temp_db

    def test_schema_tables_exist(self, temp_db):
        """Test all required tables exist."""
        conn = temp_db._get_connection()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}

        assert "conversations" in tables
        assert "messages" in tables
        assert "agent_state" in tables

    def test_wal_mode_enabled(self, temp_db):
        """Test WAL mode is enabled for concurrency."""
        conn = temp_db._get_connection()
        cursor = conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal"

    def test_foreign_keys_enabled(self, temp_db):
        """Test foreign key constraints are enabled."""
        conn = temp_db._get_connection()
        cursor = conn.execute("PRAGMA foreign_keys")
        enabled = cursor.fetchone()[0]
        assert enabled == 1


class TestConversationOperations:
    """Test conversation CRUD operations."""

    def test_create_conversation(self, temp_db):
        """Test creating a new conversation."""
        conv_id = temp_db.create_conversation(
            agent_type="convo",
            provider="claude",
            model="claude-3-5-sonnet-20241022",
            title="Test Conversation",
            metadata={"key": "value"},
        )

        assert conv_id is not None
        assert len(conv_id) == 36  # UUID format

    def test_get_conversation(self, temp_db):
        """Test retrieving conversation by ID."""
        conv_id = temp_db.create_conversation(
            agent_type="convo",
            provider="claude",
            model="claude-3-5-sonnet-20241022",
            title="Test Conversation",
            metadata={"key": "value"},
        )

        conv = temp_db.get_conversation(conv_id)

        assert conv is not None
        assert conv["id"] == conv_id
        assert conv["agent_type"] == "convo"
        assert conv["provider"] == "claude"
        assert conv["model"] == "claude-3-5-sonnet-20241022"
        assert conv["title"] == "Test Conversation"
        assert conv["metadata"] == {"key": "value"}
        assert conv["message_count"] == 0

    def test_get_nonexistent_conversation(self, temp_db):
        """Test getting conversation that doesn't exist."""
        conv = temp_db.get_conversation("nonexistent-id")
        assert conv is None

    def test_list_conversations(self, temp_db):
        """Test listing conversations."""
        # Create multiple conversations
        conv1 = temp_db.create_conversation(agent_type="convo", title="Conv 1")
        conv2 = temp_db.create_conversation(agent_type="convo", title="Conv 2")
        conv3 = temp_db.create_conversation(agent_type="hello_agent", title="Conv 3")

        # List all conversations
        conversations = temp_db.list_conversations()
        assert len(conversations) == 3

        # List by agent type
        convo_convs = temp_db.list_conversations(agent_type="convo")
        assert len(convo_convs) == 2

        # List with limit
        limited = temp_db.list_conversations(limit=2)
        assert len(limited) == 2

    def test_list_conversations_ordered_by_recent(self, temp_db):
        """Test conversations are ordered by most recent."""
        conv1 = temp_db.create_conversation(agent_type="convo", title="First")
        time.sleep(1.1)  # Ensure different timestamps (SQLite timestamp precision is 1 second)
        conv2 = temp_db.create_conversation(agent_type="convo", title="Second")

        conversations = temp_db.list_conversations()
        assert conversations[0]["id"] == conv2  # Most recent first
        assert conversations[1]["id"] == conv1

    def test_update_conversation_title(self, temp_db):
        """Test updating conversation title."""
        conv_id = temp_db.create_conversation(
            agent_type="convo",
            title="Original Title",
        )

        temp_db.update_conversation_title(conv_id, "New Title")

        conv = temp_db.get_conversation(conv_id)
        assert conv["title"] == "New Title"

    def test_delete_conversation(self, temp_db):
        """Test deleting conversation."""
        conv_id = temp_db.create_conversation(agent_type="convo")

        temp_db.delete_conversation(conv_id)

        conv = temp_db.get_conversation(conv_id)
        assert conv is None

    def test_delete_conversation_cascades(self, temp_db):
        """Test deleting conversation also deletes messages and state."""
        conv_id = temp_db.create_conversation(agent_type="convo")
        temp_db.add_message(conv_id, "user", "Hello")
        temp_db.set_state(conv_id, "key", "value")

        temp_db.delete_conversation(conv_id)

        # Check messages deleted
        messages = temp_db.get_messages(conv_id)
        assert len(messages) == 0

        # Check state deleted
        state = temp_db.get_all_state(conv_id)
        assert len(state) == 0


class TestMessageOperations:
    """Test message CRUD operations."""

    def test_add_user_message(self, temp_db):
        """Test adding user message."""
        conv_id = temp_db.create_conversation(agent_type="convo")

        msg_id = temp_db.add_message(
            conversation_id=conv_id,
            role="user",
            content="Hello, world!",
            metadata={"source": "cli"},
            token_count=10,
        )

        assert msg_id is not None

    def test_add_assistant_message(self, temp_db):
        """Test adding assistant message."""
        conv_id = temp_db.create_conversation(agent_type="convo")

        msg_id = temp_db.add_message(
            conversation_id=conv_id,
            role="assistant",
            content="Hi there!",
        )

        assert msg_id is not None

    def test_add_message_invalid_role(self, temp_db):
        """Test adding message with invalid role raises error."""
        conv_id = temp_db.create_conversation(agent_type="convo")

        with pytest.raises(ValueError, match="Invalid role"):
            temp_db.add_message(
                conversation_id=conv_id,
                role="invalid",
                content="Test",
            )

    def test_get_messages(self, temp_db):
        """Test retrieving messages."""
        conv_id = temp_db.create_conversation(agent_type="convo")

        temp_db.add_message(conv_id, "user", "Message 1")
        temp_db.add_message(conv_id, "assistant", "Response 1")
        temp_db.add_message(conv_id, "user", "Message 2")

        messages = temp_db.get_messages(conv_id)

        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Message 1"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

    def test_get_messages_with_limit(self, temp_db):
        """Test retrieving messages with limit."""
        conv_id = temp_db.create_conversation(agent_type="convo")

        for i in range(5):
            temp_db.add_message(conv_id, "user", f"Message {i}")

        messages = temp_db.get_messages(conv_id, limit=3)
        assert len(messages) == 3

    def test_get_recent_messages(self, temp_db):
        """Test retrieving recent messages."""
        conv_id = temp_db.create_conversation(agent_type="convo")

        for i in range(10):
            temp_db.add_message(conv_id, "user", f"Message {i}")

        recent = temp_db.get_recent_messages(conv_id, limit=3)

        assert len(recent) == 3
        # Should get last 3 messages in chronological order
        assert recent[0]["content"] == "Message 7"
        assert recent[1]["content"] == "Message 8"
        assert recent[2]["content"] == "Message 9"

    def test_message_increments_count(self, temp_db):
        """Test message count is auto-incremented."""
        conv_id = temp_db.create_conversation(agent_type="convo")

        temp_db.add_message(conv_id, "user", "Message 1")
        temp_db.add_message(conv_id, "assistant", "Response 1")

        conv = temp_db.get_conversation(conv_id)
        assert conv["message_count"] == 2

    def test_message_updates_timestamp(self, temp_db):
        """Test adding message updates conversation timestamp."""
        conv_id = temp_db.create_conversation(agent_type="convo")

        conv_before = temp_db.get_conversation(conv_id)
        time.sleep(1.1)  # SQLite timestamp precision is 1 second

        temp_db.add_message(conv_id, "user", "Message")

        conv_after = temp_db.get_conversation(conv_id)
        assert conv_after["updated_at"] > conv_before["updated_at"]


class TestAgentStateOperations:
    """Test agent state CRUD operations."""

    def test_set_state(self, temp_db):
        """Test setting agent state."""
        conv_id = temp_db.create_conversation(agent_type="convo")

        temp_db.set_state(conv_id, "counter", 42)
        temp_db.set_state(conv_id, "name", "Alice")

        value = temp_db.get_state(conv_id, "counter")
        assert value == 42

    def test_get_nonexistent_state(self, temp_db):
        """Test getting state that doesn't exist."""
        conv_id = temp_db.create_conversation(agent_type="convo")

        value = temp_db.get_state(conv_id, "nonexistent")
        assert value is None

    def test_update_existing_state(self, temp_db):
        """Test updating existing state value."""
        conv_id = temp_db.create_conversation(agent_type="convo")

        temp_db.set_state(conv_id, "counter", 1)
        temp_db.set_state(conv_id, "counter", 2)

        value = temp_db.get_state(conv_id, "counter")
        assert value == 2

    def test_get_all_state(self, temp_db):
        """Test retrieving all state."""
        conv_id = temp_db.create_conversation(agent_type="convo")

        temp_db.set_state(conv_id, "key1", "value1")
        temp_db.set_state(conv_id, "key2", 42)
        temp_db.set_state(conv_id, "key3", {"nested": "object"})

        state = temp_db.get_all_state(conv_id)

        assert len(state) == 3
        assert state["key1"] == "value1"
        assert state["key2"] == 42
        assert state["key3"] == {"nested": "object"}

    def test_delete_state(self, temp_db):
        """Test deleting state."""
        conv_id = temp_db.create_conversation(agent_type="convo")

        temp_db.set_state(conv_id, "key", "value")
        temp_db.delete_state(conv_id, "key")

        value = temp_db.get_state(conv_id, "key")
        assert value is None

    def test_state_complex_types(self, temp_db):
        """Test state supports complex JSON types."""
        conv_id = temp_db.create_conversation(agent_type="convo")

        complex_value = {
            "list": [1, 2, 3],
            "nested": {"a": 1, "b": 2},
            "boolean": True,
            "null": None,
        }

        temp_db.set_state(conv_id, "complex", complex_value)
        value = temp_db.get_state(conv_id, "complex")

        assert value == complex_value


class TestTransactions:
    """Test transaction handling."""

    def test_transaction_commit(self, temp_db):
        """Test transaction commits successfully."""
        conv_id = temp_db.create_conversation(agent_type="convo")

        with temp_db.transaction():
            temp_db.add_message(conv_id, "user", "Message 1")
            temp_db.add_message(conv_id, "assistant", "Response 1")

        messages = temp_db.get_messages(conv_id)
        assert len(messages) == 2

    def test_transaction_rollback(self, temp_db):
        """Test transaction rolls back on error."""
        conv_id = temp_db.create_conversation(agent_type="convo")

        try:
            with temp_db.transaction():
                temp_db.add_message(conv_id, "user", "Message 1")
                raise Exception("Simulated error")
        except Exception:
            pass

        # Transaction should have rolled back
        messages = temp_db.get_messages(conv_id)
        assert len(messages) == 0


class TestThreadSafety:
    """Test thread safety of database operations."""

    def test_concurrent_message_adds(self, temp_db):
        """Test concurrent message additions are thread-safe."""
        conv_id = temp_db.create_conversation(agent_type="convo")

        def add_messages(start_idx):
            for i in range(start_idx, start_idx + 10):
                temp_db.add_message(conv_id, "user", f"Message {i}")

        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_messages, args=(i * 10,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        messages = temp_db.get_messages(conv_id)
        assert len(messages) == 50

    def test_thread_local_connections(self, temp_db):
        """Test each thread gets its own connection."""
        connections = []

        def get_connection():
            conn = temp_db._get_connection()
            connections.append(id(conn))

        threads = []
        for _ in range(3):
            thread = threading.Thread(target=get_connection)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # Each thread should get a different connection
        assert len(set(connections)) == 3
