"""Memory service for managing conversation persistence.

Provides business logic layer on top of DatabaseManager for conversation
lifecycle, history management, and state persistence.
"""

from typing import Any, Dict, List, Optional

from src.core.db import DatabaseManager
from src.core.logger import get_logger

logger = get_logger(__name__)


class MemoryService:
    """Business logic layer for conversation persistence.

    Provides high-level operations for managing conversations, messages,
    and agent state. Wraps DatabaseManager with business logic like
    auto-title generation and history formatting.
    """

    def __init__(self, db_manager: DatabaseManager):
        """Initialize memory service.

        Args:
            db_manager: DatabaseManager instance to use for persistence.
        """
        self.db = db_manager
        logger.debug("MemoryService initialized")

    def create_conversation(
        self,
        agent_type: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new conversation.

        Args:
            agent_type: Type of agent (e.g., "convo", "hello_agent").
            provider: LLM provider (e.g., "claude", "openai").
            model: Model name.
            metadata: Additional metadata as dict.

        Returns:
            Conversation ID (UUID).
        """
        conversation_id = self.db.create_conversation(
            agent_type=agent_type,
            provider=provider,
            model=model,
            title=None,  # Auto-generated on first message
            metadata=metadata,
        )

        logger.info(f"Created conversation {conversation_id} for {agent_type}")
        return conversation_id

    def load_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Load full conversation with messages and metadata.

        Args:
            conversation_id: Conversation UUID.

        Returns:
            Dict with conversation info and messages, or None if not found.
        """
        conversation = self.db.get_conversation(conversation_id)
        if conversation is None:
            logger.warning(f"Conversation {conversation_id} not found")
            return None

        # Load all messages
        messages = self.db.get_messages(conversation_id)

        return {
            "conversation": conversation,
            "messages": messages,
        }

    def save_turn(
        self,
        conversation_id: str,
        user_message: str,
        assistant_message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Save a conversation turn (user message + assistant response).

        Args:
            conversation_id: Conversation UUID.
            user_message: User's message.
            assistant_message: Assistant's response.
            metadata: Optional metadata for the turn.

        This method:
        1. Saves both messages to database
        2. Auto-generates title if this is the first turn
        3. Updates conversation timestamp
        """
        # Save user message
        self.db.add_message(
            conversation_id=conversation_id,
            role="user",
            content=user_message,
            metadata=metadata,
        )

        # Save assistant message
        self.db.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_message,
            metadata=metadata,
        )

        # Auto-generate title if this is the first turn
        conversation = self.db.get_conversation(conversation_id)
        if conversation and conversation["message_count"] == 2 and not conversation["title"]:
            title = self._generate_title(user_message)
            self.db.update_conversation_title(conversation_id, title)
            logger.debug(f"Auto-generated title: {title}")

        logger.debug(f"Saved turn for conversation {conversation_id}")

    def get_history_for_context(
        self,
        conversation_id: str,
        max_messages: int = 10,
    ) -> List[Dict[str, str]]:
        """Get recent conversation history formatted for LLM context.

        Args:
            conversation_id: Conversation UUID.
            max_messages: Maximum number of recent messages to retrieve.

        Returns:
            List of dicts with 'role' and 'content' keys, suitable for
            passing to LLM APIs.
        """
        messages = self.db.get_recent_messages(conversation_id, limit=max_messages)

        # Format for LLM context
        formatted = []
        for msg in messages:
            formatted.append({
                "role": msg["role"],
                "content": msg["content"],
            })

        return formatted

    def save_state(self, conversation_id: str, state: Dict[str, Any]):
        """Save all agent state for conversation.

        Args:
            conversation_id: Conversation UUID.
            state: Dict of state key-value pairs to save.
        """
        for key, value in state.items():
            self.db.set_state(conversation_id, key, value)

        logger.debug(f"Saved {len(state)} state keys for conversation {conversation_id}")

    def load_state(self, conversation_id: str) -> Dict[str, Any]:
        """Load all agent state for conversation.

        Args:
            conversation_id: Conversation UUID.

        Returns:
            Dict of all state key-value pairs.
        """
        state = self.db.get_all_state(conversation_id)
        logger.debug(f"Loaded {len(state)} state keys for conversation {conversation_id}")
        return state

    def list_recent_conversations(
        self,
        agent_type: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """List recent conversations.

        Args:
            agent_type: Filter by agent type (None = all).
            limit: Maximum number of conversations to return.

        Returns:
            List of conversation dicts ordered by most recent.
        """
        conversations = self.db.list_conversations(
            agent_type=agent_type,
            limit=limit,
        )

        return conversations

    def set_conversation_title(self, conversation_id: str, title: str):
        """Set conversation title.

        Args:
            conversation_id: Conversation UUID.
            title: New title.
        """
        self.db.update_conversation_title(conversation_id, title)
        logger.info(f"Updated title for conversation {conversation_id}")

    def delete_conversation(self, conversation_id: str):
        """Delete conversation and all related data.

        Args:
            conversation_id: Conversation UUID.
        """
        self.db.delete_conversation(conversation_id)
        logger.info(f"Deleted conversation {conversation_id}")

    def _generate_title(self, first_message: str) -> str:
        """Generate conversation title from first user message.

        Args:
            first_message: First user message in conversation.

        Returns:
            Generated title (truncated to 50 chars).
        """
        # Simple truncation for now
        # Future: Use LLM to generate semantic title
        title = first_message.strip()

        if len(title) > 50:
            title = title[:47] + "..."

        return title
