"""Integration tests for tool system with agents."""

import json
from unittest.mock import Mock, patch, MagicMock
import pytest

from src.core import BaseAgent, AgentFactory
from src.core.tools import ToolRegistry, ToolExecutor, ToolResult


# Test agent concrete implementation
class TestAgent(BaseAgent):
    """Concrete test agent for testing."""

    def run(self, input_data, **kwargs):
        return f"Test: {input_data}"


class TestToolIntegration:
    """Test integration between tools and agents."""

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_agent_with_tools_enabled(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test that agent can be initialized with tools enabled."""
        # Setup mocks
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"
        mock_client_class.return_value = mock_client

        # Import tools to register them
        import src.tools  # noqa: F401

        # Create agent with tools
        agent = TestAgent(
            name="test_agent",
            enable_tools=True,
            tools=["file_read", "bash"],
        )

        assert agent.enable_tools is True
        assert agent.available_tools == ["file_read", "bash"]
        assert agent.tool_executor is not None
        assert isinstance(agent.tool_executor, ToolExecutor)

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_agent_without_tools(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test that agent works without tools."""
        # Setup mocks
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"
        mock_client_class.return_value = mock_client

        # Create agent without tools
        agent = TestAgent(
            name="test_agent",
            enable_tools=False,
        )

        assert agent.enable_tools is False
        assert agent.available_tools == []
        assert agent.tool_executor is None

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    @patch("subprocess.run")
    def test_use_tool_manual_execution(
        self, mock_subprocess, mock_client_class, mock_get_logger, mock_env_vars
    ):
        """Test manually executing a tool via use_tool method."""
        # Setup mocks
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"
        mock_client_class.return_value = mock_client

        # Mock subprocess for bash tool
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "test output"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result

        # Import tools
        import src.tools  # noqa: F401

        # Create agent with tools
        agent = TestAgent(
            name="test_agent",
            enable_tools=True,
            tools=["bash"],
        )

        # Execute tool
        result = agent.use_tool("bash", command="echo hello")

        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.output["stdout"] == "test output"
        assert len(agent.tool_history) == 1

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_use_tool_raises_when_disabled(self, mock_client_class, mock_get_logger, mock_env_vars):
        """Test that use_tool raises error when tools are disabled."""
        # Setup mocks
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"
        mock_client_class.return_value = mock_client

        # Create agent without tools
        agent = TestAgent(
            name="test_agent",
            enable_tools=False,
        )

        # Should raise error
        with pytest.raises(RuntimeError, match="Tools not enabled"):
            agent.use_tool("bash", command="echo hello")

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_chat_with_tools_fallback_to_regular_chat(
        self, mock_client_class, mock_get_logger, mock_env_vars
    ):
        """Test that chat_with_tools falls back to regular chat when tools disabled."""
        # Setup mocks
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"

        # Mock chat_completion
        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "Hello!"
        mock_message.tool_calls = None
        mock_response.choices = [Mock(message=mock_message)]
        mock_client.chat_completion.return_value = mock_response

        mock_client_class.return_value = mock_client

        # Create agent without tools
        agent = TestAgent(
            name="test_agent",
            enable_tools=False,
        )

        # Call chat_with_tools - should fall back to regular chat
        response = agent.chat_with_tools("hello")

        # Should have called chat_completion once (regular chat)
        assert mock_client.chat_completion.call_count == 1
        # Verify no tools were passed
        call_kwargs = mock_client.chat_completion.call_args[1]
        assert "tools" not in call_kwargs or call_kwargs.get("tools") is None

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    @patch("subprocess.run")
    def test_chat_with_tools_executes_tool_calls(
        self, mock_subprocess, mock_client_class, mock_get_logger, mock_env_vars
    ):
        """Test that chat_with_tools executes tool calls requested by LLM."""
        # Setup mocks
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"

        # Mock subprocess for bash tool
        mock_cmd_result = Mock()
        mock_cmd_result.returncode = 0
        mock_cmd_result.stdout = "Hello World"
        mock_cmd_result.stderr = ""
        mock_subprocess.return_value = mock_cmd_result

        # First response: LLM requests tool call
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "bash"
        mock_tool_call.function.arguments = '{"command": "echo Hello"}'

        mock_first_message = Mock()
        mock_first_message.content = "I'll execute that command"
        mock_first_message.tool_calls = [mock_tool_call]

        mock_first_response = Mock()
        mock_first_response.choices = [Mock(message=mock_first_message)]

        # Second response: LLM provides final answer
        mock_second_message = Mock()
        mock_second_message.content = "The command output: Hello World"
        mock_second_message.tool_calls = None

        mock_second_response = Mock()
        mock_second_response.choices = [Mock(message=mock_second_message)]

        # Configure mock to return different responses on successive calls
        mock_client.chat_completion.side_effect = [
            mock_first_response,
            mock_second_response,
        ]

        mock_client_class.return_value = mock_client

        # Import tools
        import src.tools  # noqa: F401

        # Create agent with tools
        agent = TestAgent(
            name="test_agent",
            enable_tools=True,
            tools=["bash"],
        )

        # Call chat_with_tools
        response = agent.chat_with_tools("run echo Hello")

        # Should have called chat_completion twice
        assert mock_client.chat_completion.call_count == 2

        # First call should include tools
        first_call_kwargs = mock_client.chat_completion.call_args_list[0][1]
        assert "tools" in first_call_kwargs
        assert first_call_kwargs["tool_choice"] == "auto"

        # Should have executed the tool
        assert len(agent.tool_history) == 1
        assert agent.tool_history[0]["tool"] == "bash"

        # Final response should be from LLM
        assert response.choices[0].message.content == "The command output: Hello World"

    @patch("src.core.agent.get_logger")
    @patch("src.core.agent.AIClientWrapper")
    def test_chat_with_tools_max_iterations(
        self, mock_client_class, mock_get_logger, mock_env_vars
    ):
        """Test that chat_with_tools respects max iterations limit."""
        # Setup mocks
        mock_client = Mock()
        mock_client.current_provider = "claude"
        mock_client.get_default_model.return_value = "claude-sonnet-4-5"

        # Mock tool call that never stops
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_123"
        mock_tool_call.function.name = "bash"
        mock_tool_call.function.arguments = '{"command": "echo loop"}'

        mock_message = Mock()
        mock_message.content = "Looping..."
        mock_message.tool_calls = [mock_tool_call]

        mock_response = Mock()
        mock_response.choices = [Mock(message=mock_message)]

        # Always return tool call request
        mock_client.chat_completion.return_value = mock_response

        mock_client_class.return_value = mock_client

        # Import tools
        import src.tools  # noqa: F401

        # Create agent with tools
        agent = TestAgent(
            name="test_agent",
            enable_tools=True,
            tools=["bash"],
        )

        # Call with low max_iterations
        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = Mock(
                returncode=0, stdout="output", stderr=""
            )

            response = agent.chat_with_tools("loop", max_tool_iterations=3)

        # Should have called chat_completion exactly 3 times
        assert mock_client.chat_completion.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
