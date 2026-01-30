import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigLoader:
    """Loads and manages configuration from YAML file."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the config loader.

        Args:
            config_path: Path to the config YAML file. If None, uses default location.
        """
        if config_path is None:
            # Default to config.yaml in the project root
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config.yaml"

        self.config_path = Path(config_path)
        self._config: Optional[Dict[str, Any]] = None

    def load(self) -> Dict[str, Any]:
        """
        Load configuration from YAML file.

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, "r") as f:
            self._config = yaml.safe_load(f)

        return self._config

    @property
    def config(self) -> Dict[str, Any]:
        """Get the loaded configuration, loading if necessary."""
        if self._config is None:
            self.load()
        return self._config

    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """
        Get configuration for a specific provider.

        Args:
            provider: Provider name (e.g., 'claude', 'gemini', 'openai')

        Returns:
            Provider configuration dictionary

        Raises:
            ValueError: If provider not found in config
        """
        providers = self.config.get("providers", {})
        if provider not in providers:
            raise ValueError(
                f"Provider '{provider}' not found in config. "
                f"Available providers: {list(providers.keys())}"
            )

        return providers[provider]

    def get_default_provider(self) -> str:
        """Get the default provider name from config."""
        return self.config.get("default_provider", "claude")

    def get_global_settings(self) -> Dict[str, Any]:
        """Get global settings from config."""
        return self.config.get("settings", {})

    def get_api_key(self, provider: str) -> str:
        """
        Get API key for a provider from environment variables.

        Args:
            provider: Provider name (e.g., 'claude', 'gemini', 'openai', 'ollama')

        Returns:
            API key from environment. Returns "not-needed" for local providers.

        Raises:
            ValueError: If API key not found and provider requires it
        """
        # Map provider names to environment variable names
        env_var_map = {
            "claude": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
        }

        # Check if provider config specifies it doesn't need an API key
        provider_config = self.get_provider_config(provider)
        requires_api_key = provider_config.get("requires_api_key", True)

        if not requires_api_key:
            # Local providers like Ollama, LlamaCpp don't need API keys
            return "not-needed"

        # Try to get env var from map, or use convention: {PROVIDER}_API_KEY
        env_var = env_var_map.get(provider.lower())
        if not env_var:
            # Convention-based: PROVIDER_API_KEY (e.g., OLLAMA_API_KEY)
            env_var = f"{provider.upper()}_API_KEY"

        api_key = os.getenv(env_var)
        if not api_key:
            # Check if there's a default_api_key in provider config (for testing)
            api_key = provider_config.get("default_api_key")

        if not api_key:
            raise ValueError(
                f"API key not found in environment. "
                f"Please set {env_var} in your .env file"
            )

        return api_key
