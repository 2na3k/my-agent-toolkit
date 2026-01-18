import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from src.core.config_loader import ConfigLoader


class TestConfigLoader:
    """Test suite for ConfigLoader class."""

    def test_init_with_custom_path(self, temp_config_file):
        """Test initialization with custom config path."""
        loader = ConfigLoader(temp_config_file)
        assert loader.config_path == Path(temp_config_file)

    def test_init_with_default_path(self):
        """Test initialization with default config path."""
        loader = ConfigLoader()
        expected_path = Path(__file__).parent.parent / "config.yaml"
        assert loader.config_path == expected_path

    def test_load_config_success(self, temp_config_file):
        """Test successful configuration loading."""
        loader = ConfigLoader(temp_config_file)
        config = loader.load()

        assert config is not None
        assert "providers" in config
        assert "claude" in config["providers"]
        assert "gemini" in config["providers"]
        assert "openai" in config["providers"]
        assert config["default_provider"] == "claude"

    def test_load_config_file_not_found(self):
        """Test loading config when file doesn't exist."""
        loader = ConfigLoader("/nonexistent/path/config.yaml")

        with pytest.raises(FileNotFoundError, match="Config file not found"):
            loader.load()

    def test_config_property_lazy_loading(self, temp_config_file):
        """Test that config property lazy loads configuration."""
        loader = ConfigLoader(temp_config_file)
        assert loader._config is None

        config = loader.config
        assert loader._config is not None
        assert config == loader._config

    def test_get_provider_config_success(self, temp_config_file):
        """Test getting configuration for a specific provider."""
        loader = ConfigLoader(temp_config_file)
        loader.load()

        claude_config = loader.get_provider_config("claude")
        assert claude_config["base_url"] == "https://api.anthropic.com/v1/"
        assert claude_config["default_model"] == "claude-sonnet-4-5"
        assert "claude-opus-4" in claude_config["models"]

    def test_get_provider_config_invalid_provider(self, temp_config_file):
        """Test getting config for non-existent provider."""
        loader = ConfigLoader(temp_config_file)
        loader.load()

        with pytest.raises(ValueError, match="Provider 'invalid' not found"):
            loader.get_provider_config("invalid")

    def test_get_default_provider(self, temp_config_file):
        """Test getting default provider."""
        loader = ConfigLoader(temp_config_file)
        loader.load()

        default = loader.get_default_provider()
        assert default == "claude"

    def test_get_global_settings(self, temp_config_file):
        """Test getting global settings."""
        loader = ConfigLoader(temp_config_file)
        loader.load()

        settings = loader.get_global_settings()
        assert settings["temperature"] == 0.7
        assert settings["max_tokens"] == 4096
        assert settings["stream"] is False

    def test_get_api_key_claude(self, temp_config_file, mock_env_vars):
        """Test getting API key for Claude provider."""
        loader = ConfigLoader(temp_config_file)

        api_key = loader.get_api_key("claude")
        assert api_key == "mock-anthropic-key-12345"

    def test_get_api_key_gemini(self, temp_config_file, mock_env_vars):
        """Test getting API key for Gemini provider."""
        loader = ConfigLoader(temp_config_file)

        api_key = loader.get_api_key("gemini")
        assert api_key == "mock-gemini-key-67890"

    def test_get_api_key_openai(self, temp_config_file, mock_env_vars):
        """Test getting API key for OpenAI provider."""
        loader = ConfigLoader(temp_config_file)

        api_key = loader.get_api_key("openai")
        assert api_key == "mock-openai-key-abcde"

    def test_get_api_key_unknown_provider(self, temp_config_file):
        """Test getting API key for unknown provider."""
        loader = ConfigLoader(temp_config_file)

        with pytest.raises(ValueError, match="Unknown provider"):
            loader.get_api_key("unknown")

    def test_get_api_key_missing_env_var(self, temp_config_file, monkeypatch):
        """Test getting API key when environment variable is not set."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        loader = ConfigLoader(temp_config_file)

        with pytest.raises(ValueError, match="API key not found in environment"):
            loader.get_api_key("claude")

    def test_multiple_provider_configs(self, temp_config_file):
        """Test accessing multiple provider configurations."""
        loader = ConfigLoader(temp_config_file)
        loader.load()

        providers = ["claude", "gemini", "openai"]
        for provider in providers:
            config = loader.get_provider_config(provider)
            assert "base_url" in config
            assert "default_model" in config
            assert "models" in config
            assert isinstance(config["models"], list)

    def test_config_immutability(self, temp_config_file):
        """Test that modifying returned config doesn't affect cached config."""
        loader = ConfigLoader(temp_config_file)
        config1 = loader.config

        # Modify the returned config
        config1["test_key"] = "test_value"

        # Get config again
        config2 = loader.config

        # Both should reference the same object (cached)
        assert config1 is config2
