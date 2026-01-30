# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based agent toolkit for building AI-powered agents that can use multiple LLM providers (Claude, Gemini, OpenAI) through a unified interface. The project uses the OpenAI SDK as a common interface for all providers.

**Key Features:**
- **Intelligent Agent Routing**: Metadata-based routing system that automatically directs inputs to specialized agents
- **Conversation Orchestration**: ConvoAgent manages chat workflow with automatic routing and LLM fallback
- **CLI Interface**: Command-line tool (`aa`) for interactive chat and direct agent invocation
- **Web UI**: FastAPI backend and React frontend for web-based interaction
- **Multi-Provider Support**: Unified interface for Claude, Gemini, and OpenAI

## Development Commands

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_agent.py

# Run specific test
pytest tests/test_agent.py::TestBaseAgent::test_init_with_default_provider
```

### Environment Setup
```bash
# Install dependencies (using uv)
uv sync

# Install dev dependencies
uv sync --group dev
```

### CLI Commands

The toolkit includes a command-line interface (`aa`) with five main commands:

```bash
# Interactive chat mode
aa chat                                    # Start REPL-style chat
aa chat --provider gemini                  # Chat with specific provider
aa chat --no-router                        # Direct LLM (bypass router)

# Direct agent invocation
aa invoke -a hello_agent -m "hello"        # Invoke specific agent
aa invoke -a convo -m "analyze this" -f document.pdf  # With file attachment
aa invoke -a convo -m "hello" --format json  # JSON output

# List available agents
aa agents                                  # Show all registered agents

# Version information
aa version                                 # Show toolkit version

# Start web servers
aa ui                                      # Start both API and UI servers
aa ui --api-only                           # Start only API server (port 8000)
aa ui --ui-only                            # Start only UI server (port 5173)
```

**Chat Mode Special Commands:**
- `/help`, `/h` - Show available commands
- `/exit`, `/quit`, `/q` - Exit chat
- `/reset`, `/clear` - Reset conversation history
- `/context`, `/c` - Show conversation context
- `/agents` - List available agents
- `/history` - Show conversation history

For complete CLI documentation, see `src/cli/README.md`.

## Architecture

### Core Components

1. **src/core/agent.py** - Base agent framework
   - `BaseAgent`: Abstract base class all agents inherit from. Provides AI client management, logging, conversation history, and state management.
   - `AgentFactory`: Factory for creating and registering agent instances with routing metadata
   - `@register_agent` decorator: Registers agent classes with routing metadata (patterns, keywords, priority, enabled status)

2. **src/core/client.py** - Unified AI client wrapper
   - `AIClientWrapper`: Wraps OpenAI SDK to work with multiple providers (Claude, Gemini, OpenAI)
   - `ClientFactory`: Creates and manages client instances for different providers
   - All providers use OpenAI SDK interface via their compatible APIs

3. **src/core/config_loader.py** - Configuration management
   - Loads settings from `config.yaml` at project root
   - Maps providers to API keys from environment variables:
     - Claude: `ANTHROPIC_API_KEY`
     - Gemini: `GEMINI_API_KEY`
     - OpenAI: `OPENAI_API_KEY`

4. **src/core/logger.py** - Centralized logging
   - Use `get_logger(name)` for consistent logging across agents

5. **src/agents/router/** - Intelligent routing system
   - `RouterAgent`: Routes inputs to specialized agents based on metadata
   - `RoutingEngine`: Orchestrates routing strategies with confidence thresholds
   - `MetadataBasedStrategy`: Pattern and keyword matching strategy
   - `RouteExecutor`: Handles agent lifecycle and execution
   - Uses Strategy Pattern for pluggable routing logic
   - Agents self-declare routing rules via `@register_agent` decorator

6. **src/agents/convo/** - Main conversation orchestrator
   - `ConvoAgent`: Primary entry point for chat interactions
   - Routes to specialized agents when high-confidence match exists (≥0.7)
   - Falls back to direct LLM conversation when no match or low confidence
   - Maintains conversation history and context
   - Configurable router usage and confidence thresholds

7. **src/cli/** - Command-line interface
   - `ChatInterface`: Interactive REPL-style chat with Rich display
   - `AgentInvoker`: One-shot agent invocation with file attachments
   - `FileHandler`: Supports text, images (base64), PDFs (base64)
   - `OutputFormatter`: Rich-based formatting with markdown rendering

### Agent Development Pattern

To create a new agent:

1. Inherit from `BaseAgent`
2. Implement the abstract `run(input_data, **kwargs)` method
3. Register using `@register_agent()` decorator with routing metadata
4. Use `self.chat()` to interact with LLMs
5. Use `self.logger` for logging
6. Use `self.state` and `self.history` for maintaining agent state

**Basic Example:**
```python
from src.core import BaseAgent, register_agent

@register_agent("my_agent")
class MyAgent(BaseAgent):
    def run(self, input_data, **kwargs):
        response = self.chat(f"Process this: {input_data}")
        return response
```

**Example with Routing Metadata:**
```python
from src.core import BaseAgent, register_agent

@register_agent(
    "deepresearch",
    patterns=[r"research", r"find\s+information", r"look\s+up"],
    keywords=["research", "investigate", "find", "search"],
    description="Performs deep research with web search and citations",
    priority=10,  # Higher priority than default agents
    enabled=True  # Available for routing (default)
)
class DeepResearchAgent(BaseAgent):
    def run(self, input_data, **kwargs):
        # Research implementation
        results = self._perform_research(input_data)
        return self._format_results(results)
```

**Routing Metadata Parameters:**
- `agent_type` (required): Unique identifier for the agent
- `patterns` (optional): List of regex patterns that should route to this agent
- `keywords` (optional): List of keywords that should route to this agent
- `description` (optional): Human-readable description of agent capabilities
- `priority` (optional): Higher priority agents checked first (default: 0)
- `enabled` (optional): Whether agent is available for routing (default: True)

**Important Notes:**
- Set `enabled=False` for agents that shouldn't be auto-routed (RouterAgent, ConvoAgent)
- Higher confidence matches (pattern matching > keyword matching)
- Priority is used as tiebreaker when confidence is equal
- Agents are automatically discovered via AgentFactory metadata

### Configuration System

- **config.yaml**: Defines providers, models, base URLs, and global settings
- Supports runtime provider/model switching via `switch_provider()` and `switch_model()`
- Default provider is set in config.yaml under `default_provider`
- Each provider has its own default model and list of available models

### Router System Architecture

The router system enables intelligent routing of inputs to specialized agents using a metadata-based strategy pattern.

**Architecture:**
```
ConvoAgent (main entry point)
    └── RouterAgent (routes to specialized agents)
            └── RoutingEngine (orchestrates strategies)
                    ├── MetadataBasedStrategy (pattern/keyword matching)
                    └── RouteExecutor (agent lifecycle management)
```

**Components:**

1. **RouterAgent** (`src/agents/router/agent.py`)
   - Inherits from BaseAgent
   - Provides `route()` and `execute_route()` methods
   - Stores routing information in state
   - Marked with `enabled=False` to prevent routing loops

2. **RoutingEngine** (`src/agents/router/engine.py`)
   - Orchestrates routing strategies
   - Configurable confidence threshold (default: 0.5)
   - Falls back to default agent when no high-confidence match
   - Supports multiple strategies (currently: metadata-based)

3. **MetadataBasedStrategy** (`src/agents/router/strategies/metadata.py`)
   - Queries AgentFactory for agent metadata
   - Pattern matching (regex) with confidence 1.0
   - Keyword matching with confidence based on match ratio (max 0.8)
   - Sorts agents by priority (higher first)
   - Returns highest confidence match with priority as tiebreaker

4. **RouteExecutor** (`src/agents/router/executor.py`)
   - Creates target agent via AgentFactory
   - Executes agent's `run()` method
   - Handles errors and logging

**Data Models** (`src/agents/router/models.py`):
```python
@dataclass
class RouteMatch:
    agent_type: str           # e.g., "hello_agent"
    confidence: float         # 0.0 to 1.0
    metadata: Dict[str, Any]  # Pattern matched, keywords, etc.
    strategy_name: str        # Which strategy produced this match

@dataclass
class RouteResult:
    matched: bool
    route_match: Optional[RouteMatch]
    fallback_agent: Optional[str] = None
    error: Optional[str] = None
```

**How Routing Works:**

1. Input received by ConvoAgent
2. ConvoAgent calls `router.route(input, context)`
3. RoutingEngine queries MetadataBasedStrategy
4. Strategy checks all routable agents (sorted by priority):
   - Check patterns (regex) → confidence 1.0 if match
   - Check keywords → confidence based on match ratio
5. Return highest confidence match (priority as tiebreaker)
6. If confidence ≥ threshold → Route to specialized agent
7. If confidence < threshold → Use fallback (LLM conversation)

**Example Routing Decision:**
```
Input: "hello there"

MetadataBasedStrategy:
  - Check HelloAgent (priority 0):
    - Pattern r"^hello\b" matches → confidence 1.0
  - Check OtherAgent (priority 5):
    - No pattern match, keyword "hello" matches → confidence 0.5

Result: Route to HelloAgent (confidence 1.0 > threshold 0.7)
```

**Adding Routing to New Agents:**

Agents automatically participate in routing by declaring metadata in `@register_agent`:

```python
@register_agent(
    "my_agent",
    patterns=[r"pattern1", r"pattern2"],  # Regex patterns
    keywords=["keyword1", "keyword2"],     # Keywords for matching
    priority=10,                           # Higher = checked first
    enabled=True                           # Available for routing
)
class MyAgent(BaseAgent):
    # ...
```

**Future Extensions:**
- LLMIntentStrategy: Intelligent routing using LLM to determine intent
- Agent caching: Pool frequently used agents
- Metrics/monitoring: Track routing performance
- Dynamic route reloading: Hot-reload metadata without restart

### Testing Infrastructure

- Uses pytest with fixtures in `tests/conftest.py`
- Mock fixtures available for config files, environment variables, and OpenAI responses
- Tests should use `temp_config_file` and `mock_env_vars` fixtures to avoid requiring real API keys
- Test coverage includes:
  - **Core tests**: `test_config_loader.py`, `test_client.py`, `test_agent.py`
  - **Agent tests**: `test_hello_agent.py`, `test_router.py` (20 tests), `test_convo.py` (14 tests)
  - **CLI tests**: `test_cli_e2e.py` (5 end-to-end tests)

### Example Agents

#### ConvoAgent (`src/agents/convo/`)
The main conversation orchestrator and primary entry point for chat interactions.

**Key Features:**
- Routes to specialized agents when high-confidence match exists (default threshold: 0.7)
- Falls back to direct LLM conversation when no match or low confidence
- Maintains conversation history and context across interactions
- Configurable router usage (`use_router=True/False`)

**Usage:**
```python
from src.core import AgentFactory

# Create via factory (recommended)
agent = AgentFactory.create("convo")

# With custom configuration
agent = AgentFactory.create(
    "convo",
    use_router=True,
    router_confidence_threshold=0.7,
    provider="claude"
)

# Run with routing
result = agent.run("hello")  # Routes to HelloAgent
result = agent.run("tell me about Python")  # Falls back to LLM

# Disable router for pure LLM mode
agent = AgentFactory.create("convo", use_router=False)
result = agent.run("anything")  # Direct LLM conversation
```

**Workflow:**
1. Input received
2. If router enabled: Check for specialized agent match
3. If high confidence (≥0.7): Route to specialized agent
4. If low confidence or no router: Direct LLM conversation
5. Return result with conversation history maintained

#### HelloAgent (`src/agents/hello_agent/`)
A simple example agent demonstrating routing metadata and basic agent pattern.

**Registration:**
```python
@register_agent(
    "hello_agent",
    patterns=[r"^hello\b", r"^hi\b", r"^hey\b", r"greet", r"say hello"],
    keywords=["hello", "hi", "greet", "greeting", "hey"],
    description="A simple agent that always returns 'hello'",
    priority=0,
)
class HelloAgent(BaseAgent):
    # ...
```

**Usage:**
```python
from src.agents.hello_agent import HelloAgent

# Create instance
agent = HelloAgent()

# Run returns "hello"
result = agent.run("anything")  # Returns: "hello"

# Greet method with optional name
greeting = agent.greet("World")  # Returns: "hello, World!"
```

**Routing Behavior:**
- Matches greetings: "hello", "hi", "hey", "greet me", etc.
- Used automatically by ConvoAgent when greeting patterns detected
- Priority 0 (default priority)

## Key Design Decisions

1. **OpenAI SDK as Universal Interface**: Instead of provider-specific SDKs, uses OpenAI SDK with different base URLs to create a consistent interface across all providers

2. **Factory Pattern**: Agents are registered with `AgentFactory` using decorators, allowing dynamic agent creation and discovery

3. **Separation of Concerns**: Core functionality (client, config, logging) is separated from agent implementations (in src/agents/)

4. **Environment-based Secrets**: API keys are never in code or config files, only in environment variables loaded via .env file

5. **Type Flexibility**: The `run()` method accepts `Any` type for input_data, allowing for multimodal inputs including text, images, and structured data. All three providers (Claude, GPT-4o, Gemini) support vision capabilities.

6. **Metadata-Driven Routing**: Agents self-declare their routing rules via the `@register_agent` decorator, eliminating the need for separate configuration files. The router automatically discovers and routes to agents via AgentFactory metadata.

## Web UI and API

The toolkit includes a web-based interface built with FastAPI (backend) and React (frontend).

**Starting the servers:**
```bash
# Start both API and UI
aa ui

# Start only API server (http://localhost:8000)
aa ui --api-only

# Start only UI server (http://localhost:5173)
aa ui --ui-only

# Or use Make directly
make run-all    # Both servers
make run-api    # API only
make run-ui     # UI only
```

**API Server** (`src/api/`):
- FastAPI application on port 8000
- RESTful endpoints for agent interaction
- Run with: `uv run uvicorn src.api.main:app --reload`

**UI Server** (`src/ui/`):
- React frontend on port 5173
- Interactive chat interface
- Run with: `cd src/ui && bun run dev`

**Architecture:**
- API and UI run as separate services
- API provides backend logic and agent execution
- UI provides web-based chat interface
- Services can be run independently or together

## Important Implementation Notes

### Adding New Providers

To add a new provider to the system:

1. **Update config.yaml**: Add the provider configuration
   ```yaml
   providers:
     new_provider:
       base_url: "https://api.newprovider.com/v1/"
       default_model: "new-model-name"
       models:
         - "new-model-name"
         - "new-model-other"
       timeout: 30
       max_retries: 3
   ```

2. **Set environment variable**: Add API key to .env file
   ```bash
   NEW_PROVIDER_API_KEY=your_api_key_here
   ```

3. **Update env_var_map**: Modify `src/core/config_loader.py`
   ```python
   env_var_map = {
       'claude': 'ANTHROPIC_API_KEY',
       'gemini': 'GEMINI_API_KEY',
       'openai': 'OPENAI_API_KEY',
       'new_provider': 'NEW_PROVIDER_API_KEY'  # Add this line
   }
   ```

   **Note**: A future improvement would be to use convention-based naming (e.g., `{PROVIDER_NAME}_API_KEY`) to avoid updating the code when adding providers.

### Agent State Management

BaseAgent provides built-in state management:

- `set_state(key, value)`: Store agent-specific state
- `get_state(key, default=None)`: Retrieve state values
- `reset_state()`: Clear all state
- `history`: List of conversation turns (automatically managed by `chat()`)
- `clear_history()`: Clear conversation history

### Provider and Model Switching

Agents support runtime provider/model switching:

```python
agent = MyAgent(provider="claude")

# Switch to different provider
agent.switch_provider("openai")

# Switch to different model
agent.switch_model("gpt-4o")
```

### CLI File Attachments

The CLI supports file attachments via the `invoke` command:

**Supported File Types:**
- **Text files**: `.txt`, `.md`, `.py`, `.js`, `.json`, `.yaml`, `.csv` (read as UTF-8)
- **Images**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp` (base64 encoded)
- **PDFs**: `.pdf` (base64 encoded)

**File Size Limit**: 10MB per file

**Usage:**
```bash
# Single file
aa invoke -a convo -m "analyze this code" -f script.py

# Multiple files
aa invoke -a convo -m "compare these" -f doc1.pdf -f doc2.pdf

# Images for vision models
aa invoke -a convo -m "describe this" -f photo.jpg
```

### CLI Output Formats

**Text Format (default)**: Rich markdown rendering with syntax highlighting
```bash
aa invoke -a convo -m "explain Python"
```

**JSON Format**: Structured JSON output for programmatic use
```bash
aa invoke -a convo -m "hello" --format json
# Output: {"result": "Hello! How can I assist you?"}
```

**Save to File**:
```bash
aa invoke -a convo -m "hello" --output result.txt
```

### Testing Best Practices

When writing tests:

1. Always use `@patch('src.core.agent.get_logger')` and `@patch('src.core.agent.AIClientWrapper')`
2. Use `mock_env_vars` fixture to avoid requiring real API keys
3. Mock the client's `current_provider` and `get_default_model()` return values
4. For testing chat functionality, mock `chat_completion()` return value with proper structure
5. Avoid naming test classes with "Agent" suffix (pytest warning)
6. For router tests, mock `AgentFactory.get_routable_agents()` to return test metadata
7. For ConvoAgent tests, mock both the router and LLM responses

## Quick Reference

### Common Workflows

**1. Interactive Chat Session:**
```bash
# Start chat with default provider (Claude)
aa chat

# Chat with specific provider
aa chat --provider gemini --model gemini-2.0-flash-exp

# Pure LLM mode (no routing)
aa chat --no-router
```

**2. Direct Agent Invocation:**
```bash
# Invoke specific agent
aa invoke -a hello_agent -m "hello"

# With conversation agent (routing enabled)
aa invoke -a convo -m "hello there"

# With file attachment
aa invoke -a convo -m "summarize this" -f document.pdf
```

**3. Creating a New Agent:**
```python
# 1. Create agent file: src/agents/my_agent/agent.py
from src.core import BaseAgent, register_agent

@register_agent(
    "my_agent",
    patterns=[r"my.*pattern"],
    keywords=["keyword1", "keyword2"],
    description="Agent description",
    priority=5
)
class MyAgent(BaseAgent):
    def run(self, input_data, **kwargs):
        # Agent logic
        return self.chat(f"Process: {input_data}")

# 2. Create __init__.py: src/agents/my_agent/__init__.py
from .agent import MyAgent
__all__ = ["MyAgent"]

# 3. Register in src/agents/__init__.py
import src.agents.my_agent  # noqa: F401

# 4. Verify registration
aa agents  # Should show my_agent in list
```

**4. Running Tests:**
```bash
# All tests
pytest

# Specific test file
pytest tests/test_router.py

# With coverage
pytest --cov=src --cov-report=term-missing

# Specific test
pytest tests/test_router.py::test_router_initialization
```

**5. Starting Web Services:**
```bash
# Both API and UI
aa ui

# API only (for development)
aa ui --api-only

# UI only (if API running separately)
aa ui --ui-only
```

### Environment Variables

Required API keys (set in `.env` file):
```bash
ANTHROPIC_API_KEY=your_claude_key
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
```

### Project Structure

```
my-agent-toolkit/
├── src/
│   ├── core/              # Core framework (agent, client, config, logger)
│   ├── agents/            # Agent implementations
│   │   ├── convo/        # Main conversation orchestrator
│   │   ├── router/       # Intelligent routing system
│   │   └── hello_agent/  # Example agent
│   ├── cli/              # Command-line interface
│   ├── api/              # FastAPI backend
│   └── ui/               # React frontend
├── tests/                # Test suite
├── config.yaml           # Provider and model configuration
├── pyproject.toml        # Project dependencies and metadata
├── Makefile              # Build and run commands
└── CLAUDE.md             # This file
```

### Troubleshooting

**"Agent not found" error:**
```bash
# List available agents
aa agents

# Verify agent is registered
python -c "from src.core import AgentFactory; print(AgentFactory.list_agents())"
```

**"API key not found" error:**
```bash
# Check .env file exists
cat .env

# Verify environment variables loaded
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('ANTHROPIC_API_KEY'))"
```

**Router not routing to expected agent:**
```bash
# Check agent metadata
python -c "from src.core import AgentFactory; import src.agents; print(AgentFactory.get_all_metadata())"

# Test routing with verbose logging
aa invoke -a convo -m "test input" --verbose
```

**Tests failing:**
```bash
# Install dev dependencies
uv sync --group dev

# Clear pytest cache
rm -rf .pytest_cache
rm -rf **/__pycache__

# Run tests again
pytest -v
```

## Custom Provider Integration

The toolkit supports **any OpenAI-compatible API provider**, including local LLM runners and custom endpoints.

### Built-in Provider Examples

The `config.yaml` includes example configurations for popular local providers:

- **Ollama** (localhost:11434) - Most popular local LLM runner
- **LlamaCpp** (localhost:8080) - C++ implementation
- **LM Studio** (localhost:1234) - GUI-based local runner

### Quick Start with Ollama

```bash
# Install and start Ollama
ollama serve

# Pull a model with function calling support
ollama pull qwen2.5:latest

# Use with the toolkit
aa chat --provider ollama --model qwen2.5:latest
> run the command: ls -la
```

### Adding Custom Providers

1. **Add provider to `config.yaml`**:

```yaml
providers:
  my_provider:
    base_url: "http://localhost:PORT/v1/"
    default_model: "model-name"
    requires_api_key: false  # For local providers
    default_api_key: "not-needed"
    timeout: 120
```

2. **Use in CLI**:

```bash
aa chat --provider my_provider
```

3. **Use in code**:

```python
agent = AgentFactory.create("convo", provider="my_provider")
```

### Tool Support with Custom Providers

Tools work with **any provider that supports OpenAI function calling format**. This includes:

✅ **Compatible Models**:
- Ollama: qwen2.5, llama3.2, mistral
- LlamaCpp: With `--chat-format functionary`
- LM Studio: Check model compatibility
- vLLM: Built-in support

⚠️ **Limitations**:
- Older models may not support function calling
- Some local providers require specific configuration
- Performance varies based on hardware

### Detailed Guide

See **[CUSTOM_PROVIDERS.md](CUSTOM_PROVIDERS.md)** for:
- Complete setup instructions for Ollama, LlamaCpp, LM Studio
- Function calling compatibility matrix
- Troubleshooting common issues
- Advanced configuration options
- Example use cases

