import os
import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def mock_config_yaml():
    """Fixture providing mock YAML configuration content."""
    return """
providers:
  claude:
    base_url: "https://api.anthropic.com/v1/"
    default_model: "claude-sonnet-4-5"
    models:
      - "claude-sonnet-4-5"
      - "claude-opus-4"
      - "claude-haiku-3-5"
    timeout: 60
    max_retries: 3

  gemini:
    base_url: "https://generativelanguage.googleapis.com/v1beta/openai/"
    default_model: "gemini-3-flash-preview"
    models:
      - "gemini-3-flash-preview"
      - "gemini-2.0-flash-exp"
    timeout: 60
    max_retries: 3

  openai:
    base_url: "https://api.openai.com/v1/"
    default_model: "gpt-4o"
    models:
      - "gpt-4o"
      - "gpt-4o-mini"
      - "gpt-4-turbo"
    timeout: 60
    max_retries: 3

default_provider: "claude"

settings:
  temperature: 0.7
  max_tokens: 4096
  stream: false
"""


@pytest.fixture
def temp_config_file(mock_config_yaml):
    """Fixture providing a temporary config file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(mock_config_yaml)
        temp_path = f.name

    yield temp_path

    # Cleanup
    os.unlink(temp_path)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture to set mock environment variables for API keys."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "mock-anthropic-key-12345")
    monkeypatch.setenv("GEMINI_API_KEY", "mock-gemini-key-67890")
    monkeypatch.setenv("OPENAI_API_KEY", "mock-openai-key-abcde")


@pytest.fixture
def mock_openai_response():
    """Fixture providing a mock OpenAI chat completion response."""
    return {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1677652288,
        "model": "claude-sonnet-4-5",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "This is a mock response from the AI.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }


@pytest.fixture
def mock_stream_response():
    """Fixture providing a mock streaming response."""
    return [
        {
            "id": "chatcmpl-123",
            "choices": [{"delta": {"content": "Hello"}, "index": 0}],
        },
        {
            "id": "chatcmpl-123",
            "choices": [{"delta": {"content": " world"}, "index": 0}],
        },
        {
            "id": "chatcmpl-123",
            "choices": [{"delta": {}, "index": 0, "finish_reason": "stop"}],
        },
    ]
