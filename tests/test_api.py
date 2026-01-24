"""Tests for FastAPI endpoints with persistence."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from src.api.main import app, memory_service


@pytest.fixture
def temp_db_path():
    """Create a temporary database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def client(temp_db_path):
    """Create test client with temporary database."""
    from src.core.db import DatabaseManager
    from src.core.memory import MemoryService

    # Reset singleton instance to force new instance with temp database
    DatabaseManager._instance = None

    # Create real instances using temp database
    db_manager = DatabaseManager(temp_db_path)
    mem_service = MemoryService(db_manager)

    # Set the global variable directly
    import src.api.main
    original_memory_service = src.api.main.memory_service
    src.api.main.memory_service = mem_service

    with TestClient(app) as test_client:
        yield test_client

    # Cleanup
    db_manager.close()
    src.api.main.memory_service = original_memory_service

    # Reset singleton for next test
    DatabaseManager._instance = None


@pytest.fixture
def mock_agent_response():
    """Mock response from agent.chat()."""
    response = Mock()
    response.choices = [Mock()]
    response.choices[0].message.content = "Test response from agent"
    return response


class TestAgentEndpoints:
    """Test agent listing endpoints."""

    def test_list_agents(self, client):
        """Test GET /agents returns all registered agents."""
        response = client.get("/agents")

        assert response.status_code == 200
        agents = response.json()
        assert isinstance(agents, list)
        assert len(agents) > 0

        # Check structure
        for agent in agents:
            assert "id" in agent
            assert "description" in agent
            assert "metadata" in agent

        # Should include at least hello_agent and convo
        agent_ids = [a["id"] for a in agents]
        assert "hello_agent" in agent_ids
        assert "convo" in agent_ids


class TestConversationCRUD:
    """Test conversation CRUD endpoints."""

    def test_create_conversation(self, client):
        """Test POST /conversations creates a new conversation."""
        response = client.post(
            "/conversations",
            json={
                "agent_type": "convo",
                "provider": "claude",
                "model": "claude-3-5-sonnet-20241022",
                "title": "Test Conversation"
            }
        )

        assert response.status_code == 201
        data = response.json()

        assert "id" in data
        assert data["agent_type"] == "convo"
        assert data["provider"] == "claude"
        assert data["model"] == "claude-3-5-sonnet-20241022"
        assert data["title"] == "Test Conversation"
        assert data["message_count"] == 0

    def test_create_conversation_invalid_agent(self, client):
        """Test POST /conversations with invalid agent type."""
        response = client.post(
            "/conversations",
            json={
                "agent_type": "nonexistent_agent"
            }
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_create_conversation_auto_title(self, client):
        """Test POST /conversations without title (auto-generated later)."""
        response = client.post(
            "/conversations",
            json={
                "agent_type": "hello_agent"
            }
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] is None  # Will be auto-generated on first message

    def test_list_conversations_empty(self, client):
        """Test GET /conversations returns empty list initially."""
        response = client.get("/conversations")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_conversations(self, client):
        """Test GET /conversations returns all conversations."""
        # Create a few conversations
        conv1 = client.post("/conversations", json={"agent_type": "convo"})
        conv2 = client.post("/conversations", json={"agent_type": "hello_agent"})

        response = client.get("/conversations")

        assert response.status_code == 200
        conversations = response.json()
        assert len(conversations) == 2

        # Verify both conversations are present (order may vary with same timestamp)
        conv_ids = {c["id"] for c in conversations}
        assert conv1.json()["id"] in conv_ids
        assert conv2.json()["id"] in conv_ids

    def test_list_conversations_filter_by_agent_type(self, client):
        """Test GET /conversations with agent_type filter."""
        # Create conversations with different agent types
        client.post("/conversations", json={"agent_type": "convo"})
        conv2 = client.post("/conversations", json={"agent_type": "hello_agent"})

        response = client.get("/conversations?agent_type=hello_agent")

        assert response.status_code == 200
        conversations = response.json()
        assert len(conversations) == 1
        assert conversations[0]["id"] == conv2.json()["id"]

    def test_list_conversations_pagination(self, client):
        """Test GET /conversations with limit and offset."""
        # Create multiple conversations
        for i in range(5):
            client.post("/conversations", json={"agent_type": "convo"})

        # Get first 2
        response = client.get("/conversations?limit=2&offset=0")
        assert response.status_code == 200
        assert len(response.json()) == 2

        # Get next 2
        response = client.get("/conversations?limit=2&offset=2")
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_get_conversation(self, client):
        """Test GET /conversations/{id} returns specific conversation."""
        # Create conversation
        create_response = client.post(
            "/conversations",
            json={"agent_type": "convo", "title": "Test"}
        )
        conversation_id = create_response.json()["id"]

        # Get conversation
        response = client.get(f"/conversations/{conversation_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conversation_id
        assert data["title"] == "Test"

    def test_get_conversation_not_found(self, client):
        """Test GET /conversations/{id} with non-existent ID."""
        response = client.get("/conversations/nonexistent-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_conversation_title(self, client):
        """Test PATCH /conversations/{id} updates title."""
        # Create conversation
        create_response = client.post("/conversations", json={"agent_type": "convo"})
        conversation_id = create_response.json()["id"]

        # Update title
        response = client.patch(
            f"/conversations/{conversation_id}",
            json={"title": "Updated Title"}
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"

    def test_update_conversation_not_found(self, client):
        """Test PATCH /conversations/{id} with non-existent ID."""
        response = client.patch(
            "/conversations/nonexistent-id",
            json={"title": "New Title"}
        )

        assert response.status_code == 404

    def test_delete_conversation(self, client):
        """Test DELETE /conversations/{id} deletes conversation."""
        # Create conversation
        create_response = client.post("/conversations", json={"agent_type": "convo"})
        conversation_id = create_response.json()["id"]

        # Delete conversation
        response = client.delete(f"/conversations/{conversation_id}")
        assert response.status_code == 204

        # Verify deletion
        get_response = client.get(f"/conversations/{conversation_id}")
        assert get_response.status_code == 404

    def test_delete_conversation_not_found(self, client):
        """Test DELETE /conversations/{id} with non-existent ID."""
        response = client.delete("/conversations/nonexistent-id")
        assert response.status_code == 404


class TestMessages:
    """Test message-related endpoints."""

    def test_get_messages_empty(self, client):
        """Test GET /conversations/{id}/messages for new conversation."""
        # Create conversation
        create_response = client.post("/conversations", json={"agent_type": "convo"})
        conversation_id = create_response.json()["id"]

        response = client.get(f"/conversations/{conversation_id}/messages")

        assert response.status_code == 200
        assert response.json() == []

    def test_get_messages_not_found(self, client):
        """Test GET /conversations/{id}/messages with non-existent conversation."""
        response = client.get("/conversations/nonexistent-id/messages")
        assert response.status_code == 404


class TestChat:
    """Test chat endpoint with persistence."""

    @patch('src.core.agent.AIClientWrapper')
    def test_chat_creates_agent_with_persistence(self, mock_client_class, client, mock_agent_response):
        """Test POST /chat creates agent with conversation_id and memory_service."""
        # Setup mock
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"
        mock_client_instance.chat_completion.return_value = mock_agent_response

        # Create conversation
        create_response = client.post(
            "/conversations",
            json={"agent_type": "convo", "provider": "claude"}
        )
        conversation_id = create_response.json()["id"]

        # Send chat message
        with patch('src.core.agent.get_logger'):
            response = client.post(
                "/chat",
                json={
                    "conversation_id": conversation_id,
                    "message": "Hello"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == conversation_id
        assert data["user_message"] == "Hello"
        assert data["assistant_message"] == "Test response from agent"
        assert data["status"] == "success"

    @patch('src.core.agent.AIClientWrapper')
    def test_chat_persists_messages(self, mock_client_class, client, mock_agent_response):
        """Test POST /chat persists messages to database."""
        # Setup mock
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"
        mock_client_instance.chat_completion.return_value = mock_agent_response

        # Create conversation
        create_response = client.post("/conversations", json={"agent_type": "convo"})
        conversation_id = create_response.json()["id"]

        # Send chat message
        with patch('src.core.agent.get_logger'):
            client.post(
                "/chat",
                json={
                    "conversation_id": conversation_id,
                    "message": "Test message"
                }
            )

        # Verify messages were persisted
        messages_response = client.get(f"/conversations/{conversation_id}/messages")
        assert messages_response.status_code == 200

        messages = messages_response.json()
        assert len(messages) == 2  # user + assistant
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Test message"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Test response from agent"

    @patch('src.core.agent.AIClientWrapper')
    def test_chat_auto_generates_title(self, mock_client_class, client, mock_agent_response):
        """Test POST /chat auto-generates title on first message."""
        # Setup mock
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"
        mock_client_instance.chat_completion.return_value = mock_agent_response

        # Create conversation without title
        create_response = client.post("/conversations", json={"agent_type": "convo"})
        conversation_id = create_response.json()["id"]

        # Send first message
        with patch('src.core.agent.get_logger'):
            client.post(
                "/chat",
                json={
                    "conversation_id": conversation_id,
                    "message": "This is my first message for testing"
                }
            )

        # Check that title was auto-generated
        conv_response = client.get(f"/conversations/{conversation_id}")
        conversation = conv_response.json()
        assert conversation["title"] is not None
        assert "This is my first message" in conversation["title"]

    def test_chat_conversation_not_found(self, client):
        """Test POST /chat with non-existent conversation."""
        response = client.post(
            "/chat",
            json={
                "conversation_id": "nonexistent-id",
                "message": "Hello"
            }
        )

        assert response.status_code == 404


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check(self, client):
        """Test GET /health returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "2.0.0"
        assert data["persistence"] == "enabled"


class TestIntegration:
    """Integration tests for full conversation flow."""

    @patch('src.core.agent.AIClientWrapper')
    def test_full_conversation_flow(self, mock_client_class, client):
        """Test complete conversation lifecycle."""
        # Setup mock
        mock_client_instance = Mock()
        mock_client_class.return_value = mock_client_instance
        mock_client_instance.current_provider = "claude"
        mock_client_instance.get_default_model.return_value = "claude-3-5-sonnet-20241022"

        # Create different responses for each turn
        response1 = Mock()
        response1.choices = [Mock()]
        response1.choices[0].message.content = "First response"

        response2 = Mock()
        response2.choices = [Mock()]
        response2.choices[0].message.content = "Second response"

        mock_client_instance.chat_completion.side_effect = [response1, response2]

        with patch('src.core.agent.get_logger'):
            # 1. Create conversation
            create_response = client.post(
                "/conversations",
                json={
                    "agent_type": "convo",
                    "provider": "claude",
                    "title": "Integration Test"
                }
            )
            assert create_response.status_code == 201
            conversation_id = create_response.json()["id"]

            # 2. Send first message
            chat1 = client.post(
                "/chat",
                json={
                    "conversation_id": conversation_id,
                    "message": "First message"
                }
            )
            assert chat1.status_code == 200
            assert chat1.json()["assistant_message"] == "First response"

            # 3. Send second message
            chat2 = client.post(
                "/chat",
                json={
                    "conversation_id": conversation_id,
                    "message": "Second message"
                }
            )
            assert chat2.status_code == 200
            assert chat2.json()["assistant_message"] == "Second response"

            # 4. Get conversation - should have 4 messages total
            conv = client.get(f"/conversations/{conversation_id}")
            assert conv.json()["message_count"] == 4

            # 5. Get messages
            messages = client.get(f"/conversations/{conversation_id}/messages")
            assert len(messages.json()) == 4

            # 6. Update title
            update = client.patch(
                f"/conversations/{conversation_id}",
                json={"title": "Updated Title"}
            )
            assert update.json()["title"] == "Updated Title"

            # 7. List conversations
            conversations = client.get("/conversations")
            assert len(conversations.json()) >= 1

            # 8. Delete conversation
            delete = client.delete(f"/conversations/{conversation_id}")
            assert delete.status_code == 204

            # 9. Verify deletion
            get_deleted = client.get(f"/conversations/{conversation_id}")
            assert get_deleted.status_code == 404
