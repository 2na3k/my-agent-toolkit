# Conversation Agent (ConvoAgent)

Main entry point and orchestrator for the chat workflow. The ConvoAgent intelligently routes user inputs to specialized agents when appropriate, or handles conversations directly using LLM.

## Overview

ConvoAgent provides a seamless conversation experience by:

1. **Intent Detection** - Analyzes user input to determine if specialized agents should handle it
2. **Smart Routing** - Routes to specialized agents (via RouterAgent) when high-confidence matches exist
3. **LLM Fallback** - Handles general conversation directly with LLM when no specialized agent is appropriate
4. **Context Management** - Maintains conversation history and state across interactions

## Architecture

```
User Input
    ↓
ConvoAgent (Entry Point)
    ↓
RouterAgent (Intent Detection)
    ↓
┌────────────────┬──────────────────┐
│ High Confidence│ Low Conf./Fallback│
│ Match (≥0.7)  │                  │
↓                ↓                  │
Specialized      Direct LLM ←───────┘
Agent (e.g.,     Conversation
hello_agent)
    ↓                ↓
Response        Response
```

## Usage

### Basic Usage

```python
from src.core import AgentFactory

# Create conversation agent (with router enabled by default)
convo = AgentFactory.create("convo", provider="claude")

# Have a conversation
response = convo.run("hello there")
print(response)  # Routes to hello_agent -> "hello"

response = convo.run("tell me about Python")
print(response)  # LLM conversation -> detailed response about Python
```

### Configuration Options

```python
# Custom confidence threshold for routing
convo = AgentFactory.create(
    "convo",
    provider="claude",
    router_confidence_threshold=0.8  # Higher threshold = more LLM fallback
)

# Disable router entirely (pure LLM conversation)
convo = AgentFactory.create(
    "convo",
    provider="claude",
    use_router=False  # Always use LLM, never route to specialized agents
)

# Custom model and provider
convo = AgentFactory.create(
    "convo",
    provider="gemini",
    model="gemini-2.0-flash-exp"
)
```

### Conversation Management

```python
# Get conversation context
context = convo.get_conversation_context()
print(context)
# {
#     'history_length': 2,
#     'last_input': 'tell me about Python',
#     'last_route': {'agent': 'hello_agent', 'confidence': 1.0, ...},
#     'provider': 'claude',
#     'model': 'claude-3-5-sonnet-20241022',
#     'router_enabled': True
# }

# Reset conversation (clear history and state)
convo.reset_conversation()
```

## Workflow Details

### How Routing Works

1. **Input Analysis** - ConvoAgent receives user input
2. **Router Check** - If router is enabled, checks for specialized agent matches
3. **Confidence Evaluation** - Compares match confidence against threshold (default: 0.7)
4. **Route or Fallback**:
   - **High Confidence (≥0.7)** → Execute specialized agent
   - **Low Confidence (<0.7)** → Use direct LLM conversation
   - **Fallback Route** → Always uses LLM (router found no specialized match)

### When Specialized Agents Are Used

Specialized agents are used when:
- Router finds a matching agent
- Match confidence ≥ threshold (default: 0.7)
- Match is NOT a fallback route

Examples with default hello_agent:
```python
convo.run("hello")           # → hello_agent (pattern match)
convo.run("hi there")        # → hello_agent (pattern match)
convo.run("greet me")        # → hello_agent (keyword match)
convo.run("say hello")       # → hello_agent (pattern match)
```

### When LLM is Used

LLM handles conversation when:
- No specialized agent matches
- Match confidence is below threshold
- Router returns a fallback route
- Router is disabled (`use_router=False`)
- Router encounters an error

Examples:
```python
convo.run("who are you?")                # → LLM (no specialized agent)
convo.run("tell me about Python")       # → LLM (no specialized agent)
convo.run("what's the weather?")        # → LLM (no specialized agent)
```

## API Reference

### ConvoAgent

```python
class ConvoAgent(BaseAgent):
    def __init__(
        self,
        name: str = "ConvoAgent",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        config_path: Optional[str] = None,
        use_router: bool = True,
        router_confidence_threshold: float = 0.7,
        **kwargs
    )
```

**Parameters:**
- `name` - Agent name (default: "ConvoAgent")
- `provider` - AI provider for LLM (e.g., "claude", "gemini", "openai")
- `model` - Specific model to use
- `config_path` - Path to config file
- `use_router` - Enable/disable router (default: True)
- `router_confidence_threshold` - Minimum confidence for specialized routing (default: 0.7)

### Methods

#### `run(input_data, **kwargs)`

Main conversation method. Orchestrates routing and execution.

```python
response = convo.run("hello world")
```

**Args:**
- `input_data` - User input (string)
- `**kwargs` - Additional context (e.g., temperature, max_tokens)

**Returns:**
- String response from specialized agent or LLM

#### `get_conversation_context()`

Get current conversation state and context.

```python
context = convo.get_conversation_context()
```

**Returns:**
```python
{
    'history_length': int,
    'last_input': str,
    'last_route': dict,  # Routing info if available
    'provider': str,
    'model': str,
    'router_enabled': bool
}
```

#### `reset_conversation()`

Reset conversation history and state.

```python
convo.reset_conversation()
```

## Examples

### Example 1: Mixed Conversation

```python
from src.core import AgentFactory

convo = AgentFactory.create("convo", provider="claude")

# Greetings route to hello_agent
print(convo.run("hello"))  # "hello"
print(convo.run("hi there"))  # "hello"

# General questions use LLM
print(convo.run("who are you?"))  # "I'm Claude, an AI assistant..."
print(convo.run("tell me about Python"))  # Detailed Python explanation

# Check conversation context
context = convo.get_conversation_context()
print(f"Had {context['history_length']} exchanges")
```

### Example 2: Pure LLM Mode

```python
# Disable router for pure LLM conversation
convo = AgentFactory.create("convo", provider="claude", use_router=False)

# All inputs go to LLM, even greetings
print(convo.run("hello"))  # LLM response, not "hello"
print(convo.run("tell me a joke"))  # LLM response
```

### Example 3: Custom Threshold

```python
# Higher threshold = more LLM usage
convo = AgentFactory.create(
    "convo",
    provider="claude",
    router_confidence_threshold=0.9  # Very strict routing
)

# Only very high-confidence matches route to specialized agents
# Most inputs will use LLM
```

### Example 4: Conversation Reset

```python
convo = AgentFactory.create("convo", provider="claude")

# Have some conversations
convo.run("hello")
convo.run("how are you?")
convo.run("tell me about Python")

print(len(convo.history))  # 2 (LLM conversations tracked)

# Reset for fresh start
convo.reset_conversation()
print(len(convo.history))  # 0
```

## Testing

### Run ConvoAgent Tests

```bash
# Run all convo tests
pytest tests/test_convo.py -v

# Run specific test
pytest tests/test_convo.py::TestConvoAgent::test_run_routes_to_specialized_agent -v
```

### Run End-to-End Test

```bash
python test_convo_e2e.py
```

## Design Decisions

1. **Router as Optional** - Router can be disabled for pure LLM conversations, providing flexibility

2. **Confidence Threshold** - Configurable threshold ensures quality routing decisions and prevents low-confidence matches

3. **Graceful Fallback** - Router failures don't break the conversation; system falls back to LLM

4. **History Management** - Only LLM conversations are tracked in history (specialized agents manage their own state)

5. **Entry Point Pattern** - ConvoAgent is marked as `enabled=False` to prevent routing loops

## Adding New Specialized Agents

When you add new specialized agents to the system, ConvoAgent will automatically discover and route to them via the RouterAgent. No changes to ConvoAgent are needed.

Example:
```python
@register_agent(
    "research_agent",
    patterns=[r"research", r"find\s+information"],
    keywords=["research", "investigate"],
    description="Performs deep research",
    priority=10
)
class ResearchAgent(BaseAgent):
    def run(self, input_data, **kwargs):
        return self.perform_research(input_data)
```

Now ConvoAgent will automatically route research queries to ResearchAgent:
```python
convo.run("research the history of Python")  # Routes to research_agent
```

## Future Enhancements

1. **Multi-turn Routing** - Support for multi-step workflows where routing decisions change mid-conversation
2. **Context Passing** - Pass conversation history to specialized agents for context-aware routing
3. **Streaming Support** - Enable streaming responses for better UX
4. **Custom Strategies** - Allow custom routing strategies beyond metadata-based matching

## Files

- `agent.py` - ConvoAgent implementation
- `__init__.py` - Package exports
- `README.md` - This documentation
