from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import logging
import uuid

from src.core import AgentFactory, BaseAgent
# Import all agents to ensure they are registered
import src.agents

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(
    title="Agent Toolkit API",
    description="API for interacting with AI Agents",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store
# Dict[session_id, BaseAgent]
sessions: Dict[str, BaseAgent] = {}

class ChatRequest(BaseModel):
    session_id: str
    agent_type: str
    message: str
    provider: Optional[str] = None
    model: Optional[str] = None

class AgentInfo(BaseModel):
    id: str
    description: str = ""
    metadata: Dict[str, Any] = {}

@app.get("/agents", response_model=List[AgentInfo])
async def list_agents():
    """List all available agents."""
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

@app.post("/chat")
async def chat(request: ChatRequest):
    """Send a message to an agent in a session."""
    
    # Check if session exists
    if request.session_id in sessions:
        agent = sessions[request.session_id]
        # Verify it's the same agent type? For now, assume yes or overwrite if needed.
        # Ideally, we allow switching, but let's keep it simple.
    else:
        # Create new agent instance
        if not AgentFactory.is_registered(request.agent_type):
            raise HTTPException(status_code=404, detail=f"Agent '{request.agent_type}' not found")
        
        try:
            logger.info(f"Creating new agent instance for session {request.session_id}")
            agent = AgentFactory.create(
                agent_type=request.agent_type,
                provider=request.provider,
                model=request.model
            )
            sessions[request.session_id] = agent
        except Exception as e:
            logger.error(f"Failed to create agent: {e}")
            raise HTTPException(status_code=500, detail=str(e))
            
    try:
        # Use the chat method to maintain history
        logger.info(f"Chatting with session {request.session_id}: {request.message}")
        response = agent.chat(request.message)
        
        # Extract content from response
        # OpenAI/Compatible response structure
        content = ""
        if hasattr(response, "choices") and response.choices:
            content = response.choices[0].message.content
        elif isinstance(response, str):
            content = response
        else:
            content = str(response)
            
        return {"content": content, "status": "success"}
        
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Clear a session."""
    if session_id in sessions:
        del sessions[session_id]
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=True)
