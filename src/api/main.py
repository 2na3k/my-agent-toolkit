from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.core import AgentFactory, BaseAgent
from src.core.db import DatabaseManager
from src.core.memory import MemoryService
# Import all agents to ensure they are registered
import src.agents

from logging import getLogger

logger = getLogger("api")

# Global memory service instance
memory_service: Optional[MemoryService] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - initialize and cleanup resources."""
    global memory_service

    # Startup: Initialize database and memory service
    logger.info("Initializing database and memory service...")
    db_manager = DatabaseManager.get_instance()
    memory_service = MemoryService(db_manager)
    logger.info("Memory service initialized")

    yield

    # Shutdown: Clean up resources
    logger.info("Shutting down...")
    if db_manager:
        db_manager.close()
    logger.info("Database connections closed")


app = FastAPI(
    title="Agent Toolkit API",
    description="API for interacting with AI Agents with persistent conversations",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Pydantic Models
# ============================================================================

class AgentInfo(BaseModel):
    """Information about an available agent."""
    id: str
    description: str = ""
    metadata: Dict[str, Any] = {}


class ConversationCreate(BaseModel):
    """Request to create a new conversation."""
    agent_type: str = Field(..., description="Type of agent (e.g., 'convo', 'hello_agent')")
    provider: Optional[str] = Field(None, description="LLM provider (e.g., 'claude', 'openai')")
    model: Optional[str] = Field(None, description="Model name")
    title: Optional[str] = Field(None, description="Conversation title (auto-generated if omitted)")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class ConversationResponse(BaseModel):
    """Response containing conversation details."""
    id: str
    created_at: str
    updated_at: str
    title: Optional[str]
    agent_type: str
    provider: Optional[str]
    model: Optional[str]
    metadata: Dict[str, Any]
    message_count: int


class ConversationUpdateRequest(BaseModel):
    """Request to update conversation properties."""
    title: Optional[str] = Field(None, description="New title for the conversation")


class MessageResponse(BaseModel):
    """Response containing a single message."""
    id: int
    conversation_id: str
    role: str
    content: str
    timestamp: str
    metadata: Dict[str, Any]
    token_count: Optional[int]


class ChatRequest(BaseModel):
    """Request to send a message in a conversation."""
    conversation_id: str = Field(..., description="ID of the conversation")
    message: str = Field(..., description="User message to send")


class ChatResponse(BaseModel):
    """Response from a chat message."""
    conversation_id: str
    user_message: str
    assistant_message: str
    status: str = "success"


# ============================================================================
# Agent Endpoints
# ============================================================================

@app.get("/agents", response_model=List[AgentInfo])
async def list_agents():
    """List all available agents with their metadata."""
    registered = AgentFactory.list_agents()
    agents = []
    for agent_type in registered:
        meta = AgentFactory.get_metadata(agent_type)
        agents.append(AgentInfo(
            id=agent_type,
            description=meta.get("description", ""),
            metadata=meta
        ))
    return agents


# ============================================================================
# Conversation CRUD Endpoints
# ============================================================================

@app.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(request: ConversationCreate):
    """Create a new conversation.

    This creates a persistent conversation that can be used across multiple
    chat messages. The conversation will store all messages and agent state.
    """
    if not AgentFactory.is_registered(request.agent_type):
        raise HTTPException(
            status_code=404,
            detail=f"Agent type '{request.agent_type}' not found"
        )

    try:
        conversation_id = memory_service.create_conversation(
            agent_type=request.agent_type,
            provider=request.provider,
            model=request.model,
            metadata=request.metadata or {}
        )

        # If title was provided, set it
        if request.title:
            memory_service.set_conversation_title(conversation_id, request.title)

        # Fetch and return the created conversation
        conversation = memory_service.db.get_conversation(conversation_id)

        return ConversationResponse(
            id=conversation["id"],
            created_at=conversation["created_at"],
            updated_at=conversation["updated_at"],
            title=conversation["title"],
            agent_type=conversation["agent_type"],
            provider=conversation["provider"],
            model=conversation["model"],
            metadata=conversation["metadata"],
            message_count=conversation["message_count"]
        )

    except Exception as e:
        logger.error(f"Failed to create conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    agent_type: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """List conversations ordered by most recent.

    Args:
        agent_type: Filter by agent type (optional)
        limit: Maximum number of conversations to return (default: 20)
        offset: Number of conversations to skip (default: 0)
    """
    try:
        conversations = memory_service.db.list_conversations(
            agent_type=agent_type,
            limit=limit,
            offset=offset
        )

        return [
            ConversationResponse(
                id=c["id"],
                created_at=c["created_at"],
                updated_at=c["updated_at"],
                title=c["title"],
                agent_type=c["agent_type"],
                provider=c["provider"],
                model=c["model"],
                metadata=c["metadata"],
                message_count=c["message_count"]
            )
            for c in conversations
        ]

    except Exception as e:
        logger.error(f"Failed to list conversations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str):
    """Get a specific conversation by ID."""
    try:
        conversation = memory_service.db.get_conversation(conversation_id)

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation '{conversation_id}' not found"
            )

        return ConversationResponse(
            id=conversation["id"],
            created_at=conversation["created_at"],
            updated_at=conversation["updated_at"],
            title=conversation["title"],
            agent_type=conversation["agent_type"],
            provider=conversation["provider"],
            model=conversation["model"],
            metadata=conversation["metadata"],
            message_count=conversation["message_count"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversations/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_conversation_messages(
    conversation_id: str,
    limit: Optional[int] = None,
    offset: int = 0
):
    """Get messages for a conversation.

    Args:
        conversation_id: ID of the conversation
        limit: Maximum number of messages to return (optional, default: all)
        offset: Number of messages to skip (default: 0)
    """
    try:
        # Verify conversation exists
        conversation = memory_service.db.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation '{conversation_id}' not found"
            )

        messages = memory_service.db.get_messages(
            conversation_id=conversation_id,
            limit=limit,
            offset=offset
        )

        return [
            MessageResponse(
                id=m["id"],
                conversation_id=m["conversation_id"],
                role=m["role"],
                content=m["content"],
                timestamp=m["timestamp"],
                metadata=m["metadata"],
                token_count=m["token_count"]
            )
            for m in messages
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(conversation_id: str, request: ConversationUpdateRequest):
    """Update conversation properties (currently only title).

    Args:
        conversation_id: ID of the conversation
        request: Update request with new values
    """
    try:
        # Verify conversation exists
        conversation = memory_service.db.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation '{conversation_id}' not found"
            )

        # Update title if provided
        if request.title is not None:
            memory_service.set_conversation_title(conversation_id, request.title)

        # Fetch updated conversation
        conversation = memory_service.db.get_conversation(conversation_id)

        return ConversationResponse(
            id=conversation["id"],
            created_at=conversation["created_at"],
            updated_at=conversation["updated_at"],
            title=conversation["title"],
            agent_type=conversation["agent_type"],
            provider=conversation["provider"],
            model=conversation["model"],
            metadata=conversation["metadata"],
            message_count=conversation["message_count"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/conversations/{conversation_id}", status_code=204)
async def delete_conversation(conversation_id: str):
    """Delete a conversation and all its messages and state.

    Args:
        conversation_id: ID of the conversation to delete
    """
    try:
        # Verify conversation exists
        conversation = memory_service.db.get_conversation(conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation '{conversation_id}' not found"
            )

        memory_service.delete_conversation(conversation_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete conversation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Chat Endpoint
# ============================================================================

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message in a conversation and get a response.

    This endpoint creates an agent instance with the conversation's
    configuration, sends the message, and persists both the user message
    and assistant response to the database.

    Args:
        request: Chat request with conversation_id and message
    """
    try:
        # Load conversation to get configuration
        conversation = memory_service.db.get_conversation(request.conversation_id)
        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail=f"Conversation '{request.conversation_id}' not found"
            )

        # Create agent instance with persistence enabled
        agent = AgentFactory.create(
            agent_type=conversation["agent_type"],
            provider=conversation["provider"],
            model=conversation["model"],
            conversation_id=request.conversation_id,
            memory_service=memory_service
        )

        logger.info(f"Chatting in conversation {request.conversation_id}: {request.message[:100]}")

        # Send message (this will auto-persist via agent's _update_history)
        response = agent.chat(request.message)

        # Extract content from response
        assistant_message = ""
        if hasattr(response, "choices") and response.choices:
            assistant_message = response.choices[0].message.content
        elif isinstance(response, str):
            assistant_message = response
        else:
            assistant_message = str(response)

        return ChatResponse(
            conversation_id=request.conversation_id,
            user_message=request.message,
            assistant_message=assistant_message,
            status="success"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "persistence": "enabled"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
