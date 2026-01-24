-- schema.sql
-- Database schema for conversation persistence

-- conversations table
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    title TEXT,
    agent_type TEXT NOT NULL,
    provider TEXT,
    model TEXT,
    metadata TEXT DEFAULT '{}',  -- JSON
    message_count INTEGER DEFAULT 0
);

-- messages table
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT DEFAULT '{}',  -- JSON
    token_count INTEGER,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

-- agent_state table
CREATE TABLE IF NOT EXISTS agent_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,  -- JSON
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    UNIQUE(conversation_id, key)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_conversations_created_at
    ON conversations(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_conversations_agent_type
    ON conversations(agent_type);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id
    ON messages(conversation_id);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_timestamp
    ON messages(conversation_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_agent_state_conversation_id
    ON agent_state(conversation_id);

-- Triggers for auto-updating timestamps and message count

-- Update conversations.updated_at when message is added
CREATE TRIGGER IF NOT EXISTS update_conversation_timestamp
AFTER INSERT ON messages
FOR EACH ROW
BEGIN
    UPDATE conversations
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.conversation_id;
END;

-- Increment conversations.message_count when message is added
CREATE TRIGGER IF NOT EXISTS increment_message_count
AFTER INSERT ON messages
FOR EACH ROW
BEGIN
    UPDATE conversations
    SET message_count = message_count + 1
    WHERE id = NEW.conversation_id;
END;

-- Decrement conversations.message_count when message is deleted
CREATE TRIGGER IF NOT EXISTS decrement_message_count
AFTER DELETE ON messages
FOR EACH ROW
BEGIN
    UPDATE conversations
    SET message_count = message_count - 1
    WHERE id = OLD.conversation_id;
END;

-- Update agent_state.updated_at when state value is updated
CREATE TRIGGER IF NOT EXISTS update_agent_state_timestamp
AFTER UPDATE ON agent_state
FOR EACH ROW
BEGIN
    UPDATE agent_state
    SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;
