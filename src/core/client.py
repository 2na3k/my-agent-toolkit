import os
from typing import Optional, Dict, Any, List
from openai import OpenAI
from dotenv import load_dotenv

from .config_loader import ConfigLoader
from .constants import ProviderType


class AIClientWrapper:
    """
    Unified client wrapper for multiple AI providers using OpenAI SDK.

    Supports Claude (Anthropic), Gemini, and OpenAI providers with a consistent interface.
    Configuration is loaded from config.yaml and API keys from environment variables.
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        config_path: Optional[str] = None,
        **kwargs,
    ):
        """
        Initialize the AI client wrapper.

        Args:
            provider: Provider name ('claude', 'gemini', or 'openai').
                     If None, uses default from config.
            config_path: Path to config.yaml file. If None, uses default location.
            **kwargs: Additional arguments to pass to OpenAI client
        """
        # Load environment variables
        load_dotenv()

        # Load configuration
        self.config_loader = ConfigLoader(config_path)

        # Set provider
        self.provider = provider or self.config_loader.get_default_provider()
        self.provider_config = self.config_loader.get_provider_config(self.provider)

        # Get API key from environment
        self.api_key = self.config_loader.get_api_key(self.provider)

        # Initialize OpenAI client with provider-specific settings
        client_kwargs = {
            "api_key": self.api_key,
            "base_url": self.provider_config["base_url"],
            "timeout": kwargs.get("timeout", self.provider_config.get("timeout", 60)),
            "max_retries": kwargs.get(
                "max_retries", self.provider_config.get("max_retries", 3)
            ),
        }

        # Add any additional kwargs
        for key, value in kwargs.items():
            if key not in client_kwargs:
                client_kwargs[key] = value

        self.client = OpenAI(**client_kwargs)

        # Load global settings
        self.global_settings = self.config_loader.get_global_settings()

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: Optional[bool] = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        Create a chat completion.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use. If None, uses default from config.
            temperature: Sampling temperature. If None, uses default from config.
            max_tokens: Maximum tokens to generate. If None, uses default from config.
            stream: Whether to stream the response. If None, uses default from config.
            tools: List of tool schemas for function calling. Optional.
            tool_choice: Tool choice strategy ("auto", "none", or specific tool). Optional.
            **kwargs: Additional arguments to pass to the API

        Returns:
            Chat completion response
        """
        # Use defaults from config if not provided
        model = model or self.provider_config["default_model"]
        temperature = (
            temperature
            if temperature is not None
            else self.global_settings.get("temperature", 0.7)
        )
        max_tokens = max_tokens or self.global_settings.get("max_tokens", 4096)
        stream = (
            stream if stream is not None else self.global_settings.get("stream", False)
        )

        # Build API kwargs
        api_kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }

        # Add tools if provided
        if tools:
            api_kwargs["tools"] = tools
            if tool_choice:
                api_kwargs["tool_choice"] = tool_choice

        # Add any additional kwargs
        api_kwargs.update(kwargs)

        return self.client.chat.completions.create(**api_kwargs)

    def chat_completion_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs,
    ):
        """
        Create a streaming chat completion.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use. If None, uses default from config.
            temperature: Sampling temperature. If None, uses default from config.
            max_tokens: Maximum tokens to generate. If None, uses default from config.
            **kwargs: Additional arguments to pass to the API

        Yields:
            Chat completion chunks
        """
        return self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )

    def get_available_models(self) -> List[str]:
        """
        Get list of available models for the current provider.

        Returns:
            List of model names
        """
        return self.provider_config.get("models", [])

    def get_default_model(self) -> str:
        """
        Get the default model for the current provider.

        Returns:
            Default model name
        """
        return self.provider_config["default_model"]

    def switch_provider(self, provider: str, **kwargs):
        """
        Switch to a different provider.

        Args:
            provider: Provider name ('claude', 'gemini', or 'openai')
            **kwargs: Additional arguments to pass to OpenAI client
        """
        self.__init__(
            provider=provider, config_path=self.config_loader.config_path, **kwargs
        )

    @property
    def current_provider(self) -> str:
        """Get the current provider name."""
        return self.provider

    @property
    def base_url(self) -> str:
        """Get the base URL for the current provider."""
        return self.provider_config["base_url"]

    def __repr__(self) -> str:
        return (
            f"AIClientWrapper(provider='{self.provider}', "
            f"model='{self.get_default_model()}')"
        )


class ClientFactory:
    """Factory class for dynamically creating AI clients based on configuration."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the client factory.

        Args:
            config_path: Path to config.yaml file. If None, uses default location.
        """
        self.config_loader = ConfigLoader(config_path)
        self.config_path = self.config_loader.config_path

    def get_available_providers(self) -> List[str]:
        """
        Get list of all available providers from configuration.

        Returns:
            List of provider names
        """
        providers = self.config_loader.config.get("providers", {})
        return list(providers.keys())

    def get_all_models(self) -> Dict[str, List[str]]:
        """
        Get all available models grouped by provider.

        Returns:
            Dictionary mapping provider names to their available models
        """
        providers = self.config_loader.config.get("providers", {})
        return {
            provider: config.get("models", []) for provider, config in providers.items()
        }

    def create_client(
        self, provider: Optional[str] = None, **kwargs
    ) -> AIClientWrapper:
        """
        Create an AI client wrapper for the specified provider.

        Args:
            provider: Provider name. If None, uses default from config.
            **kwargs: Additional arguments to pass to the client

        Returns:
            Configured AIClientWrapper instance

        Raises:
            ValueError: If provider is not found in configuration
        """
        if provider and provider not in self.get_available_providers():
            raise ValueError(
                f"Provider '{provider}' not found in configuration. "
                f"Available providers: {self.get_available_providers()}"
            )

        return AIClientWrapper(
            provider=provider, config_path=self.config_path, **kwargs
        )

    def create_all_clients(self, **kwargs) -> Dict[str, AIClientWrapper]:
        """
        Create client wrappers for all configured providers.

        Args:
            **kwargs: Additional arguments to pass to each client

        Returns:
            Dictionary mapping provider names to their client wrappers
        """
        clients = {}
        for provider in self.get_available_providers():
            try:
                clients[provider] = self.create_client(provider=provider, **kwargs)
            except Exception as e:
                print(f"Warning: Failed to create client for {provider}: {e}")

        return clients

    def create_client_for_model(self, model_name: str, **kwargs) -> AIClientWrapper:
        """
        Create a client wrapper based on the model name.

        Automatically detects which provider supports the given model.

        Args:
            model_name: Name of the model to use
            **kwargs: Additional arguments to pass to the client

        Returns:
            Configured AIClientWrapper instance for the detected provider

        Raises:
            ValueError: If model is not found in any provider's configuration
        """
        all_models = self.get_all_models()

        for provider, models in all_models.items():
            if model_name in models:
                return self.create_client(provider=provider, **kwargs)

        raise ValueError(
            f"Model '{model_name}' not found in any provider configuration. "
            f"Available models: {all_models}"
        )

    def get_provider_for_model(self, model_name: str) -> Optional[str]:
        """
        Get the provider name that supports the given model.

        Args:
            model_name: Name of the model

        Returns:
            Provider name if found, None otherwise
        """
        all_models = self.get_all_models()

        for provider, models in all_models.items():
            if model_name in models:
                return provider

        return None

    def __repr__(self) -> str:
        providers = self.get_available_providers()
        return f"ClientFactory(providers={providers})"
