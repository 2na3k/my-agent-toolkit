from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type

from .client import AIClientWrapper, ClientFactory
from .logger import get_logger


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
        **kwargs
    ):
        """
        Initialize the base agent.

        Args:
            name: Agent name (used for logging and identification)
            provider: AI provider ('claude', 'gemini', 'openai'). If None, uses default.
            model: Model to use. If None, uses provider's default model.
            config_path: Path to config.yaml. If None, uses default location.
            **kwargs: Additional arguments passed to the AI client
        """
        self.name = name
        self.provider = provider
        self.model = model
        self.config_path = config_path

        # Set up logger
        self.logger = get_logger(f"agent.{name}")
        self.logger.info(f"Initializing agent: {name}")

        # Initialize AI client
        try:
            self.client = AIClientWrapper(
                provider=provider,
                config_path=config_path,
                **kwargs
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
        **kwargs
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
                **kwargs
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
        recent_history = self.history[-max_history:] if len(self.history) > max_history else self.history

        for entry in recent_history:
            messages.append({"role": "user", "content": entry["user"]})
            if "assistant" in entry:
                messages.append({"role": "assistant", "content": entry["assistant"]})

        # Add new message
        messages.append({"role": "user", "content": new_message})

        return messages

    def _update_history(self, user_message: str, response: Any):
        """Update conversation history."""
        entry = {"user": user_message}

        # Extract assistant message from response
        if hasattr(response, 'choices') and response.choices:
            assistant_message = response.choices[0].message.content
            entry["assistant"] = assistant_message

        self.history.append(entry)

    def clear_history(self):
        """Clear conversation history."""
        self.history.clear()
        self.logger.info("Conversation history cleared")

    def set_state(self, key: str, value: Any):
        """Set a state variable."""
        self.state[key] = value

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
        self.logger.info(f"Switching provider from {self.client.current_provider} to {provider}")
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
    def register(cls, agent_type: str, agent_class: Type[BaseAgent], metadata: Optional[Dict] = None):
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
        **kwargs
    ) -> BaseAgent:
        """
        Create an agent instance.

        Args:
            agent_type: Type of agent to create
            name: Agent name. If None, uses agent_type.
            provider: AI provider
            model: Model to use
            config_path: Path to config file
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
            **kwargs
        )

    @classmethod
    def create_with_model(
        cls,
        agent_type: str,
        model_name: str,
        name: Optional[str] = None,
        config_path: Optional[str] = None,
        **kwargs
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
            **kwargs
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
            if metadata.get('enabled', True)
        }


# Decorator for easy agent registration
def register_agent(
    agent_type: str,
    patterns: Optional[List[str]] = None,
    keywords: Optional[List[str]] = None,
    description: Optional[str] = None,
    priority: int = 0,
    enabled: bool = True
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
            'patterns': patterns or [],
            'keywords': keywords or [],
            'description': description or agent_class.__doc__ or '',
            'priority': priority,
            'enabled': enabled
        }

        # Register with factory (existing behavior)
        AgentFactory.register(agent_type, agent_class, metadata=metadata)
        return agent_class

    return decorator