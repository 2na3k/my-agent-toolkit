"""Database manager for conversation persistence.

Provides thread-safe SQLite operations for managing conversations,
messages, and agent state.
"""

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.logger import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """Thread-safe SQLite database manager using singleton pattern.

    Uses thread-local connections for thread safety and WAL mode for
    better concurrency. Provides CRUD operations for conversations,
    messages, and agent state.
    """

    _instance = None
    _lock = threading.Lock()
    _local = threading.local()

    def __new__(cls, db_path: Optional[str] = None):
        """Singleton pattern with thread-safe initialization."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager.

        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if self._initialized:
            return

        if db_path is None:
            db_path = str(Path.home() / ".agent_toolkit" / "conversations.db")

        self.db_path = db_path
        self._initialized = True

        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize schema
        self._init_schema()

        logger.info(f"Database initialized at {self.db_path}")

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None):
        """Get singleton instance.

        Args:
            db_path: Path to SQLite database file (only used on first call).

        Returns:
            DatabaseManager instance.
        """
        return cls(db_path)

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection.

        Returns:
            Thread-local SQLite connection.
        """
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            # Enable foreign key constraints
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.connection = conn
            logger.debug(f"Created new connection for thread {threading.current_thread().name}")

        return self._local.connection

    def _in_transaction(self) -> bool:
        """Check if currently in a transaction context.

        Returns:
            True if in transaction, False otherwise.
        """
        return getattr(self._local, 'in_transaction', False)

    def _commit_if_not_in_transaction(self, conn: sqlite3.Connection):
        """Commit connection if not in a transaction context.

        Args:
            conn: Database connection to commit.
        """
        if not self._in_transaction():
            conn.commit()

    def _init_schema(self):
        """Initialize database schema from SQL file."""
        schema_path = Path(__file__).parent / "schema.sql"

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        conn = self._get_connection()
        try:
            conn.executescript(schema_sql)
            self._commit_if_not_in_transaction(conn)
            logger.debug("Database schema initialized")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise

    @contextmanager
    def transaction(self):
        """Context manager for database transactions.

        Usage:
            with db.transaction():
                db.add_message(...)
                db.set_state(...)
        """
        conn = self._get_connection()
        # Set transaction flag
        self._local.in_transaction = True
        try:
            yield conn
            conn.commit()  # Always commit at end of transaction
        except Exception as e:
            conn.rollback()
            logger.error(f"Transaction rolled back: {e}")
            raise
        finally:
            # Clear transaction flag
            self._local.in_transaction = False

    def close(self):
        """Close thread-local connection."""
        if hasattr(self._local, 'connection') and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None
            logger.debug("Connection closed")

    # Conversation CRUD operations

    def create_conversation(
        self,
        agent_type: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new conversation.

        Args:
            agent_type: Type of agent (e.g., "convo", "hello_agent").
            provider: LLM provider (e.g., "claude", "openai").
            model: Model name.
            title: Conversation title (auto-generated if None).
            metadata: Additional metadata as dict.

        Returns:
            Conversation ID (UUID).
        """
        conversation_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata or {})

        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO conversations (id, agent_type, provider, model, title, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (conversation_id, agent_type, provider, model, title, metadata_json),
            )
            self._commit_if_not_in_transaction(conn)
            logger.info(f"Created conversation {conversation_id} for agent {agent_type}")
            return conversation_id
        except sqlite3.Error as e:
            logger.error(f"Failed to create conversation: {e}")
            raise

    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation by ID.

        Args:
            conversation_id: Conversation UUID.

        Returns:
            Conversation dict or None if not found.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM conversations WHERE id = ?",
                (conversation_id,),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "id": row["id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "title": row["title"],
                "agent_type": row["agent_type"],
                "provider": row["provider"],
                "model": row["model"],
                "metadata": json.loads(row["metadata"]),
                "message_count": row["message_count"],
            }
        except sqlite3.Error as e:
            logger.error(f"Failed to get conversation {conversation_id}: {e}")
            raise

    def list_conversations(
        self,
        agent_type: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List conversations ordered by most recent.

        Args:
            agent_type: Filter by agent type (None = all).
            limit: Maximum number of conversations to return.
            offset: Number of conversations to skip.

        Returns:
            List of conversation dicts.
        """
        conn = self._get_connection()
        try:
            if agent_type is not None:
                cursor = conn.execute(
                    """
                    SELECT * FROM conversations
                    WHERE agent_type = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (agent_type, limit, offset),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM conversations
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )

            conversations = []
            for row in cursor.fetchall():
                conversations.append({
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "title": row["title"],
                    "agent_type": row["agent_type"],
                    "provider": row["provider"],
                    "model": row["model"],
                    "metadata": json.loads(row["metadata"]),
                    "message_count": row["message_count"],
                })

            return conversations
        except sqlite3.Error as e:
            logger.error(f"Failed to list conversations: {e}")
            raise

    def update_conversation_title(self, conversation_id: str, title: str):
        """Update conversation title.

        Args:
            conversation_id: Conversation UUID.
            title: New title.
        """
        conn = self._get_connection()
        try:
            conn.execute(
                "UPDATE conversations SET title = ? WHERE id = ?",
                (title, conversation_id),
            )
            self._commit_if_not_in_transaction(conn)
            logger.info(f"Updated title for conversation {conversation_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to update conversation title: {e}")
            raise

    def delete_conversation(self, conversation_id: str):
        """Delete conversation and all related messages/state.

        Args:
            conversation_id: Conversation UUID.
        """
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            self._commit_if_not_in_transaction(conn)
            logger.info(f"Deleted conversation {conversation_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to delete conversation: {e}")
            raise

    # Message CRUD operations

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        token_count: Optional[int] = None,
    ) -> int:
        """Add message to conversation.

        Args:
            conversation_id: Conversation UUID.
            role: Message role ("user" or "assistant").
            content: Message content.
            metadata: Additional metadata as dict.
            token_count: Optional token count.

        Returns:
            Message ID.
        """
        if role not in ("user", "assistant"):
            raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'")

        metadata_json = json.dumps(metadata or {})

        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content, metadata, token_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conversation_id, role, content, metadata_json, token_count),
            )
            self._commit_if_not_in_transaction(conn)
            message_id = cursor.lastrowid
            logger.debug(f"Added {role} message to conversation {conversation_id}")
            return message_id
        except sqlite3.Error as e:
            logger.error(f"Failed to add message: {e}")
            raise

    def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get messages for conversation.

        Args:
            conversation_id: Conversation UUID.
            limit: Maximum number of messages (None = all).
            offset: Number of messages to skip.

        Returns:
            List of message dicts ordered by timestamp.
        """
        conn = self._get_connection()
        try:
            # SQLite requires LIMIT with OFFSET, so use large limit if None
            actual_limit = limit if limit is not None else 999999

            cursor = conn.execute(
                """
                SELECT * FROM messages
                WHERE conversation_id = ?
                ORDER BY timestamp ASC
                LIMIT ? OFFSET ?
                """,
                (conversation_id, actual_limit, offset),
            )

            messages = []
            for row in cursor.fetchall():
                messages.append({
                    "id": row["id"],
                    "conversation_id": row["conversation_id"],
                    "role": row["role"],
                    "content": row["content"],
                    "timestamp": row["timestamp"],
                    "metadata": json.loads(row["metadata"]),
                    "token_count": row["token_count"],
                })

            return messages
        except sqlite3.Error as e:
            logger.error(f"Failed to get messages: {e}")
            raise

    def get_recent_messages(
        self,
        conversation_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get most recent messages for conversation.

        Args:
            conversation_id: Conversation UUID.
            limit: Maximum number of messages.

        Returns:
            List of recent message dicts ordered by timestamp (oldest first).
        """
        conn = self._get_connection()
        try:
            # Order by id (not timestamp) to get predictable ordering
            # even when messages are inserted rapidly with same timestamp
            cursor = conn.execute(
                """
                SELECT * FROM (
                    SELECT * FROM messages
                    WHERE conversation_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                ) AS recent_messages
                ORDER BY id ASC
                """,
                (conversation_id, limit),
            )

            messages = []
            for row in cursor.fetchall():
                messages.append({
                    "id": row["id"],
                    "conversation_id": row["conversation_id"],
                    "role": row["role"],
                    "content": row["content"],
                    "timestamp": row["timestamp"],
                    "metadata": json.loads(row["metadata"]),
                    "token_count": row["token_count"],
                })

            return messages
        except sqlite3.Error as e:
            logger.error(f"Failed to get recent messages: {e}")
            raise

    # Agent state CRUD operations

    def set_state(self, conversation_id: str, key: str, value: Any):
        """Set agent state value.

        Args:
            conversation_id: Conversation UUID.
            key: State key.
            value: State value (will be JSON serialized).
        """
        value_json = json.dumps(value)

        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO agent_state (conversation_id, key, value)
                VALUES (?, ?, ?)
                ON CONFLICT(conversation_id, key)
                DO UPDATE SET value = excluded.value, updated_at = CURRENT_TIMESTAMP
                """,
                (conversation_id, key, value_json),
            )
            self._commit_if_not_in_transaction(conn)
            logger.debug(f"Set state {key} for conversation {conversation_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to set state: {e}")
            raise

    def get_state(self, conversation_id: str, key: str) -> Optional[Any]:
        """Get agent state value.

        Args:
            conversation_id: Conversation UUID.
            key: State key.

        Returns:
            State value or None if not found.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT value FROM agent_state WHERE conversation_id = ? AND key = ?",
                (conversation_id, key),
            )
            row = cursor.fetchone()

            if row is None:
                return None

            return json.loads(row["value"])
        except sqlite3.Error as e:
            logger.error(f"Failed to get state: {e}")
            raise

    def get_all_state(self, conversation_id: str) -> Dict[str, Any]:
        """Get all agent state for conversation.

        Args:
            conversation_id: Conversation UUID.

        Returns:
            Dict of all state key-value pairs.
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT key, value FROM agent_state WHERE conversation_id = ?",
                (conversation_id,),
            )

            state = {}
            for row in cursor.fetchall():
                state[row["key"]] = json.loads(row["value"])

            return state
        except sqlite3.Error as e:
            logger.error(f"Failed to get all state: {e}")
            raise

    def delete_state(self, conversation_id: str, key: str):
        """Delete agent state value.

        Args:
            conversation_id: Conversation UUID.
            key: State key to delete.
        """
        conn = self._get_connection()
        try:
            conn.execute(
                "DELETE FROM agent_state WHERE conversation_id = ? AND key = ?",
                (conversation_id, key),
            )
            self._commit_if_not_in_transaction(conn)
            logger.debug(f"Deleted state {key} for conversation {conversation_id}")
        except sqlite3.Error as e:
            logger.error(f"Failed to delete state: {e}")
            raise
