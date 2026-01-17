# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python-based agent toolkit for building AI-powered agents that can use multiple LLM providers (Claude, Gemini, OpenAI) through a unified interface. The project uses the OpenAI SDK as a common interface for all providers.

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

## Architecture

### Core Components

1. **src/core/agent.py** - Base agent framework
   - `BaseAgent`: Abstract base class all agents inherit from. Provides AI client management, logging, conversation history, and state management.
   - `AgentFactory`: Factory for creating and registering agent instances
   - `@register_agent` decorator: Registers agent classes with the factory for easy instantiation

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

### Agent Development Pattern

To create a new agent:

1. Inherit from `BaseAgent`
2. Implement the abstract `run(input_data, **kwargs)` method
3. Register using `@register_agent("agent_name")` decorator
4. Use `self.chat()` to interact with LLMs
5. Use `self.logger` for logging
6. Use `self.state` and `self.history` for maintaining agent state

Example:
```python
from src.core import BaseAgent, register_agent

@register_agent("my_agent")
class MyAgent(BaseAgent):
    def run(self, input_data, **kwargs):
        response = self.chat(f"Process this: {input_data}")
        return response
```

### Configuration System

- **config.yaml**: Defines providers, models, base URLs, and global settings
- Supports runtime provider/model switching via `switch_provider()` and `switch_model()`
- Default provider is set in config.yaml under `default_provider`
- Each provider has its own default model and list of available models

#### Testing Infrastructure

- Uses pytest with fixtures in `tests/conftest.py`
- Mock fixtures available for config files, environment variables, and OpenAI responses
- Tests should use `temp_config_file` and `mock_env_vars` fixtures to avoid requiring real API keys
- Current test coverage: 76 tests across 4 test files
  - `test_config_loader.py`: 16 tests
  - `test_client.py`: 26 tests
  - `test_agent.py`: 23 tests
  - `test_hello_agent.py`: 11 tests

### Example Agents

#### HelloAgent (`src/agents/hello_agent/`)
A simple example agent demonstrating the basic agent pattern. Always returns "hello" regardless of input.

```python
from src.agents.hello_agent import HelloAgent

# Create instance
agent = HelloAgent()

# Run returns "hello"
result = agent.run("anything")  # Returns: "hello"

# Greet method with optional name
greeting = agent.greet("World")  # Returns: "hello, World!"
```

## Key Design Decisions

1. **OpenAI SDK as Universal Interface**: Instead of provider-specific SDKs, uses OpenAI SDK with different base URLs to create a consistent interface across all providers

2. **Factory Pattern**: Agents are registered with `AgentFactory` using decorators, allowing dynamic agent creation and discovery

3. **Separation of Concerns**: Core functionality (client, config, logging) is separated from agent implementations (in src/agents/)

4. **Environment-based Secrets**: API keys are never in code or config files, only in environment variables loaded via .env file

5. **Type Flexibility**: The `run()` method accepts `Any` type for input_data, allowing for multimodal inputs including text, images, and structured data. All three providers (Claude, GPT-4o, Gemini) support vision capabilities.

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

### Testing Best Practices

When writing tests:

1. Always use `@patch('src.core.agent.get_logger')` and `@patch('src.core.agent.AIClientWrapper')`
2. Use `mock_env_vars` fixture to avoid requiring real API keys
3. Mock the client's `current_provider` and `get_default_model()` return values
4. For testing chat functionality, mock `chat_completion()` return value with proper structure
5. Avoid naming test classes with "Agent" suffix (pytest warning)
