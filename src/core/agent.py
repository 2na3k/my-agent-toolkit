from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type, TYPE_CHECKING
import json

from .client import AIClientWrapper, ClientFactory
from .logger import get_logger

if TYPE_CHECKING:
    from .memory import MemoryService
    from .tools.registry import ToolRegistry
    from .tools.executor import ToolExecutor
    from .tools.models import ToolResult, ToolCall


class BaseAgent(ABC):
    """
    Base class for all agents in the toolkit.

    Provides common functionality for agent implementation including:
    - AI client management
    - Logging
    - Configuration handling
    - Abstract methods for agent-specific logic
    """

    def __init__(
        self,
        name: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        config_path: Optional[str] = None,
        conversation_id: Optional[str] = None,
        memory_service: Optional["MemoryService"] = None,
        tools: Optional[List[str]] = None,
        enable_tools: bool = False,
        **kwargs,
    ):
        """
        Initialize the base agent.

        Args:
            name: Agent name (used for logging and identification)
            provider: AI provider ('claude', 'gemini', 'openai'). If None, uses default.
            model: Model to use. If None, uses provider's default model.
            config_path: Path to config.yaml. If None, uses default location.
            conversation_id: Optional conversation ID for persistence. If None, no persistence.
            memory_service: Optional MemoryService for persistence. If None, no persistence.
            tools: List of tool names this agent can use. If None, no tools available.
            enable_tools: Whether to enable tool calling. Default: False.
            **kwargs: Additional arguments passed to the AI client
        """
        self.name = name
        self.provider = provider
        self.model = model
        self.config_path = config_path
        self.conversation_id = conversation_id
        self.memory_service = memory_service

        # Set up logger
        self.logger = get_logger(f"agent.{name}")
        self.logger.info(f"Initializing agent: {name}")

        # Initialize AI client
        try:
            self.client = AIClientWrapper(
                provider=provider, config_path=config_path, **kwargs
            )
            self.logger.info(
                f"AI client initialized - Provider: {self.client.current_provider}, "
                f"Model: {self.client.get_default_model()}"
            )
        except Exception as e:
            self.logger.error(f"Failed to initialize AI client: {e}")
            raise

        # Agent state
        self.state: Dict[str, Any] = {}
        self.history: List[Dict[str, Any]] = []

        # Tool support
        self.enable_tools = enable_tools
        self.available_tools = tools or []
        self.tool_executor = None
        self.tool_history: List[Dict] = []

        if self.enable_tools:
            from .tools.executor import ToolExecutor

            self.tool_executor = ToolExecutor()
            self.logger.info(f"Tools enabled: {self.available_tools}")

        # Load conversation from memory if persistence is enabled
        if self.conversation_id and self.memory_service:
            self._load_from_memory()

    def _load_from_memory(self):
        """Load conversation history and state from memory.

        This method is called during initialization if both conversation_id
        and memory_service are provided.
        """
        if not self.conversation_id or not self.memory_service:
            return

        try:
            # Load conversation data
            data = self.memory_service.load_conversation(self.conversation_id)
            if not data:
                self.logger.warning(f"Conversation {self.conversation_id} not found")
                return

            # Reconstruct history from messages
            messages = data.get("messages", [])
            self.history = []

            # Group messages into user-assistant pairs
            for i in range(0, len(messages), 2):
                if i + 1 < len(messages):
                    entry = {
                        "user": messages[i]["content"],
                        "assistant": messages[i + 1]["content"],
                    }
                    self.history.append(entry)
                elif messages[i]["role"] == "user":
                    # Dangling user message without response
                    self.history.append({"user": messages[i]["content"]})

            # Load agent state
            self.state = self.memory_service.load_state(self.conversation_id)

            self.logger.info(
                f"Loaded conversation {self.conversation_id}: "
                f"{len(self.history)} turns, {len(self.state)} state keys"
            )

        except Exception as e:
            self.logger.error(f"Failed to load from memory: {e}")
            # Continue with empty history/state rather than failing

    @abstractmethod
    def run(self, input_data: Any, **kwargs) -> Any:
        """
        Main execution method for the agent.

        Args:
            input_data: Input data for the agent to process
            **kwargs: Additional execution parameters

        Returns:
            Agent execution result
        """
        pass

    def chat(
        self,
        message: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs,
    ) -> Any:
        """
        Send a chat message to the AI model.

        Args:
            message: Message to send
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional parameters for the API

        Returns:
            AI response
        """
        messages = [{"role": "user", "content": message}]

        # Add conversation history if available
        if self.history:
            messages = self._build_messages_with_history(message)

        try:
            self.logger.debug(f"Sending chat message: {message[:100]}...")

            response = self.client.chat_completion(
                messages=messages,
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                **kwargs,
            )

            # Store in history
            self._update_history(message, response)

            return response

        except Exception as e:
            self.logger.error(f"Chat failed: {e}")
            raise

    def _build_messages_with_history(self, new_message: str) -> List[Dict[str, str]]:
        """Build messages list including conversation history."""
        messages = []

        # Add history (keep last N messages to avoid token limits)
        max_history = 10
        recent_history = (
            self.history[-max_history:]
            if len(self.history) > max_history
            else self.history
        )

        for entry in recent_history:
            messages.append({"role": "user", "content": entry["user"]})
            if "assistant" in entry:
                messages.append({"role": "assistant", "content": entry["assistant"]})

        # Add new message
        messages.append({"role": "user", "content": new_message})

        return messages

    def _update_history(self, user_message: str, response: Any):
        """Update conversation history and persist if memory_service is available."""
        entry = {"user": user_message}

        # Extract assistant message from response
        assistant_message = None
        if hasattr(response, "choices") and response.choices:
            assistant_message = response.choices[0].message.content
            entry["assistant"] = assistant_message

        # Update in-memory history
        self.history.append(entry)

        # Persist to database if memory service is available
        if self.memory_service and self.conversation_id and assistant_message:
            try:
                self.memory_service.save_turn(
                    conversation_id=self.conversation_id,
                    user_message=user_message,
                    assistant_message=assistant_message,
                )
            except Exception as e:
                self.logger.error(f"Failed to persist conversation turn: {e}")

    def clear_history(self):
        """Clear conversation history."""
        self.history.clear()
        self.logger.info("Conversation history cleared")

    def set_state(self, key: str, value: Any):
        """Set a state variable and persist if memory_service is available."""
        self.state[key] = value

        # Auto-persist state if memory service is available
        if self.memory_service and self.conversation_id:
            try:
                self.memory_service.db.set_state(self.conversation_id, key, value)
            except Exception as e:
                self.logger.error(f"Failed to persist state: {e}")

    def get_state(self, key: str, default: Any = None) -> Any:
        """Get a state variable."""
        return self.state.get(key, default)

    def reset_state(self):
        """Reset agent state."""
        self.state.clear()
        self.logger.info("Agent state reset")

    def switch_provider(self, provider: str, **kwargs):
        """
        Switch to a different AI provider.

        Args:
            provider: Provider name ('claude', 'gemini', 'openai')
            **kwargs: Additional arguments for the client
        """
        self.logger.info(
            f"Switching provider from {self.client.current_provider} to {provider}"
        )
        self.client.switch_provider(provider, **kwargs)
        self.provider = provider

    def switch_model(self, model: str):
        """
        Switch to a different model.

        Args:
            model: Model name
        """
        self.logger.info(f"Switching model to {model}")
        self.model = model

    def use_tool(self, tool_name: str, **params) -> "ToolResult":
        """
        Manually execute a tool.

        Args:
            tool_name: Name of the tool to execute
            **params: Parameters to pass to the tool

        Returns:
            ToolResult object with execution results

        Raises:
            RuntimeError: If tools are not enabled for this agent
        """
        if not self.enable_tools or not self.tool_executor:
            raise RuntimeError("Tools not enabled for this agent")

        result = self.tool_executor.execute(tool_name, params)

        # Track in history
        self.tool_history.append(
            {"tool": tool_name, "params": params, "result": result}
        )

        return result

    def chat_with_tools(
        self,
        message: str,
        max_tool_iterations: int = 5,
        **kwargs,
    ) -> Any:
        """
        Chat with automatic tool calling loop.

        The LLM can request tool calls, which are executed automatically,
        and results are fed back to the LLM for further processing.

        Args:
            message: User message to send
            max_tool_iterations: Maximum number of tool call iterations (default: 5)
            **kwargs: Additional parameters for chat_completion

        Returns:
            Final AI response after tool execution loop

        Raises:
            RuntimeError: If tools are not enabled
        """
        if not self.enable_tools or not self.available_tools:
            # Fall back to regular chat if tools not enabled
            return self.chat(message, **kwargs)

        from .tools.registry import ToolRegistry

        messages = self._build_messages_with_history(message)
        tool_schemas = ToolRegistry.get_schemas(self.available_tools)

        for iteration in range(max_tool_iterations):
            self.logger.debug(f"Tool iteration {iteration + 1}/{max_tool_iterations}")

            # Call LLM with tools
            response = self.client.chat_completion(
                messages=messages,
                model=self.model,
                tools=tool_schemas,
                tool_choice="auto",
                **kwargs,
            )

            assistant_message = response.choices[0].message

            # Check if LLM wants to call tools
            if not assistant_message.tool_calls:
                # No more tool calls - update history and return
                self._update_history(message, response)
                return response

            # Add assistant message with tool calls to messages
            messages.append(
                {
                    "role": "assistant",
                    "content": assistant_message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in assistant_message.tool_calls
                    ],
                }
            )

            # Execute each tool call
            for tool_call in assistant_message.tool_calls:
                tool_name = tool_call.function.name
                tool_params = json.loads(tool_call.function.arguments)

                self.logger.info(f"Executing tool: {tool_name}")

                # Execute tool
                try:
                    result = self.use_tool(tool_name, **tool_params)

                    # Add tool result to messages
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(
                                {
                                    "success": result.success,
                                    "output": result.output,
                                    "error": result.error,
                                }
                            ),
                        }
                    )
                except Exception as e:
                    self.logger.error(f"Tool execution failed: {e}")
                    # Add error to messages
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(
                                {"success": False, "output": None, "error": str(e)}
                            ),
                        }
                    )

        # Max iterations reached - return last response
        self.logger.warning(f"Max tool iterations ({max_tool_iterations}) reached")
        return response

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}(name='{self.name}', "
            f"provider='{self.client.current_provider}', "
            f"model='{self.model or self.client.get_default_model()}')"
        )


class AgentFactory:
    """
    Factory class for creating and managing agent instances.

    Provides:
    - Dynamic agent creation
    - Agent registration and discovery
    - Centralized agent configuration
    """

    _registered_agents: Dict[str, Type[BaseAgent]] = {}
    _agent_metadata: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(
        cls,
        agent_type: str,
        agent_class: Type[BaseAgent],
        metadata: Optional[Dict] = None,
    ):
        """
        Register an agent class with optional routing metadata.

        Args:
            agent_type: Unique identifier for the agent type
            agent_class: Agent class (must inherit from BaseAgent)
            metadata: Optional routing metadata for the agent
        """
        if not issubclass(agent_class, BaseAgent):
            raise TypeError(f"{agent_class} must inherit from BaseAgent")

        cls._registered_agents[agent_type] = agent_class
        cls._agent_metadata[agent_type] = metadata or {}

    @classmethod
    def create(
        cls,
        agent_type: str,
        name: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        config_path: Optional[str] = None,
        conversation_id: Optional[str] = None,
        memory_service: Optional["MemoryService"] = None,
        **kwargs,
    ) -> BaseAgent:
        """
        Create an agent instance.

        Args:
            agent_type: Type of agent to create
            name: Agent name. If None, uses agent_type.
            provider: AI provider
            model: Model to use
            config_path: Path to config file
            conversation_id: Optional conversation ID for persistence
            memory_service: Optional MemoryService for persistence
            **kwargs: Additional arguments for the agent

        Returns:
            Agent instance

        Raises:
            ValueError: If agent_type is not registered
        """
        if agent_type not in cls._registered_agents:
            raise ValueError(
                f"Agent type '{agent_type}' not registered. "
                f"Available types: {list(cls._registered_agents.keys())}"
            )

        agent_class = cls._registered_agents[agent_type]
        agent_name = name or agent_type

        return agent_class(
            name=agent_name,
            provider=provider,
            model=model,
            config_path=config_path,
            conversation_id=conversation_id,
            memory_service=memory_service,
            **kwargs,
        )

    @classmethod
    def create_with_model(
        cls,
        agent_type: str,
        model_name: str,
        name: Optional[str] = None,
        config_path: Optional[str] = None,
        **kwargs,
    ) -> BaseAgent:
        """
        Create an agent instance with automatic provider detection based on model.

        Args:
            agent_type: Type of agent to create
            model_name: Model name (provider will be auto-detected)
            name: Agent name
            config_path: Path to config file
            **kwargs: Additional arguments for the agent

        Returns:
            Agent instance
        """
        # Auto-detect provider from model name
        factory = ClientFactory(config_path)
        provider = factory.get_provider_for_model(model_name)

        if provider is None:
            raise ValueError(f"Model '{model_name}' not found in configuration")

        return cls.create(
            agent_type=agent_type,
            name=name,
            provider=provider,
            model=model_name,
            config_path=config_path,
            **kwargs,
        )

    @classmethod
    def list_agents(cls) -> List[str]:
        """
        List all registered agent types.

        Returns:
            List of registered agent type names
        """
        return list(cls._registered_agents.keys())

    @classmethod
    def is_registered(cls, agent_type: str) -> bool:
        """
        Check if an agent type is registered.

        Args:
            agent_type: Agent type to check

        Returns:
            True if registered, False otherwise
        """
        return agent_type in cls._registered_agents

    @classmethod
    def unregister(cls, agent_type: str):
        """
        Unregister an agent type.

        Args:
            agent_type: Agent type to unregister
        """
        if agent_type in cls._registered_agents:
            del cls._registered_agents[agent_type]
        if agent_type in cls._agent_metadata:
            del cls._agent_metadata[agent_type]

    @classmethod
    def get_metadata(cls, agent_type: str) -> Dict[str, Any]:
        """
        Get routing metadata for an agent.

        Args:
            agent_type: Agent type to get metadata for

        Returns:
            Agent metadata dictionary
        """
        return cls._agent_metadata.get(agent_type, {})

    @classmethod
    def get_all_metadata(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get routing metadata for all registered agents.

        Returns:
            Dictionary mapping agent types to their metadata
        """
        return {
            agent_type: cls.get_metadata(agent_type)
            for agent_type in cls._registered_agents.keys()
        }

    @classmethod
    def get_routable_agents(cls) -> Dict[str, Dict[str, Any]]:
        """
        Get all agents that are enabled for routing.

        Returns:
            Dictionary mapping agent types to their metadata for enabled agents
        """
        return {
            agent_type: metadata
            for agent_type, metadata in cls._agent_metadata.items()
            if metadata.get("enabled", True)
        }


# Decorator for easy agent registration
def register_agent(
    agent_type: str,
    patterns: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    description: Optional[str] = None,
    priority: int = 0,
    enabled: bool = True,
):
    """
    Decorator to register an agent class with routing metadata.

    Args:
        agent_type: Unique identifier for the agent
        patterns: Regex patterns that should route to this agent
        keywords: Keywords that should route to this agent
        description: Human-readable description of what this agent does
        priority: Higher priority agents are checked first (default: 0)
        enabled: Whether this agent is available for routing (default: True)

    Example:
        >>> @register_agent(
        >>>     "hello_agent",
        >>>     patterns=[r"^hello", r"^hi\b", r"greet"],
        >>>     keywords=["hello", "greeting", "hi"],
        >>>     description="Handles simple greetings"
        >>> )
        >>> class HelloAgent(BaseAgent):
        >>>     def run(self, input_data, **kwargs):
        >>>         return "hello"
    """

    def decorator(agent_class: Type[BaseAgent]):
        # Store routing metadata
        metadata = {
            "patterns": patterns or [],
            "keywords": keywords or [],
            "description": description or agent_class.__doc__ or "",
            "priority": priority,
            "enabled": enabled,
        }

        # Register with factory (existing behavior)
        AgentFactory.register(agent_type, agent_class, metadata=metadata)
        return agent_class

    return decorator
