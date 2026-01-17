import pytest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
from openai import OpenAI

from src.agents.client import AIClientWrapper, ClientFactory
from src.agents.config_loader import ConfigLoader


class TestAIClientWrapper:
    """Test suite for AIClientWrapper class."""

    @patch('src.agents.client.load_dotenv')
    @patch('src.agents.client.OpenAI')
    def test_init_with_default_provider(self, mock_openai_class, mock_load_dotenv, temp_config_file, mock_env_vars):
        """Test initialization with default provider."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        wrapper = AIClientWrapper(config_path=temp_config_file)

        assert wrapper.provider == 'claude'
        assert wrapper.api_key == "mock-anthropic-key-12345"
        mock_openai_class.assert_called_once()
        mock_load_dotenv.assert_called_once()

    @patch('src.agents.client.load_dotenv')
    @patch('src.agents.client.OpenAI')
    def test_init_with_specific_provider(self, mock_openai_class, mock_load_dotenv, temp_config_file, mock_env_vars):
        """Test initialization with specific provider."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        wrapper = AIClientWrapper(provider='gemini', config_path=temp_config_file)

        assert wrapper.provider == 'gemini'
        assert wrapper.api_key == "mock-gemini-key-67890"

        call_kwargs = mock_openai_class.call_args[1]
        assert call_kwargs['base_url'] == "https://generativelanguage.googleapis.com/v1beta/openai/"

    @patch('src.agents.client.load_dotenv')
    @patch('src.agents.client.OpenAI')
    def test_init_with_custom_kwargs(self, mock_openai_class, mock_load_dotenv, temp_config_file, mock_env_vars):
        """Test initialization with custom kwargs."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        wrapper = AIClientWrapper(
            provider='claude',
            config_path=temp_config_file,
            timeout=120,
            max_retries=5
        )

        call_kwargs = mock_openai_class.call_args[1]
        assert call_kwargs['timeout'] == 120
        assert call_kwargs['max_retries'] == 5

    @patch('src.agents.client.load_dotenv')
    @patch('src.agents.client.OpenAI')
    def test_chat_completion_with_defaults(self, mock_openai_class, mock_load_dotenv, temp_config_file, mock_env_vars, mock_openai_response):
        """Test chat completion with default parameters."""
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_openai_class.return_value = mock_client

        wrapper = AIClientWrapper(config_path=temp_config_file)
        messages = [{"role": "user", "content": "Hello"}]

        response = wrapper.chat_completion(messages)

        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs['model'] == 'claude-sonnet-4-5'
        assert call_kwargs['temperature'] == 0.7
        assert call_kwargs['max_tokens'] == 4096
        assert call_kwargs['stream'] is False
        assert call_kwargs['messages'] == messages

    @patch('src.agents.client.load_dotenv')
    @patch('src.agents.client.OpenAI')
    def test_chat_completion_with_custom_params(self, mock_openai_class, mock_load_dotenv, temp_config_file, mock_env_vars, mock_openai_response):
        """Test chat completion with custom parameters."""
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_openai_response
        mock_openai_class.return_value = mock_client

        wrapper = AIClientWrapper(config_path=temp_config_file)
        messages = [{"role": "user", "content": "Hello"}]

        response = wrapper.chat_completion(
            messages,
            model="claude-opus-4",
            temperature=0.5,
            max_tokens=2000,
            stream=False
        )

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs['model'] == 'claude-opus-4'
        assert call_kwargs['temperature'] == 0.5
        assert call_kwargs['max_tokens'] == 2000

    @patch('src.agents.client.load_dotenv')
    @patch('src.agents.client.OpenAI')
    def test_chat_completion_stream(self, mock_openai_class, mock_load_dotenv, temp_config_file, mock_env_vars, mock_stream_response):
        """Test streaming chat completion."""
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = iter(mock_stream_response)
        mock_openai_class.return_value = mock_client

        wrapper = AIClientWrapper(config_path=temp_config_file)
        messages = [{"role": "user", "content": "Hello"}]

        response = wrapper.chat_completion_stream(messages)

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs['stream'] is True

    @patch('src.agents.client.load_dotenv')
    @patch('src.agents.client.OpenAI')
    def test_get_available_models(self, mock_openai_class, mock_load_dotenv, temp_config_file, mock_env_vars):
        """Test getting available models."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        wrapper = AIClientWrapper(provider='claude', config_path=temp_config_file)
        models = wrapper.get_available_models()

        assert 'claude-sonnet-4-5' in models
        assert 'claude-opus-4' in models
        assert 'claude-haiku-3-5' in models

    @patch('src.agents.client.load_dotenv')
    @patch('src.agents.client.OpenAI')
    def test_get_default_model(self, mock_openai_class, mock_load_dotenv, temp_config_file, mock_env_vars):
        """Test getting default model."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        wrapper = AIClientWrapper(provider='openai', config_path=temp_config_file)
        default_model = wrapper.get_default_model()

        assert default_model == 'gpt-4o'

    @patch('src.agents.client.load_dotenv')
    @patch('src.agents.client.OpenAI')
    def test_switch_provider(self, mock_openai_class, mock_load_dotenv, temp_config_file, mock_env_vars):
        """Test switching between providers."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        wrapper = AIClientWrapper(provider='claude', config_path=temp_config_file)
        assert wrapper.provider == 'claude'

        wrapper.switch_provider('openai')
        assert wrapper.provider == 'openai'
        assert wrapper.get_default_model() == 'gpt-4o'

    @patch('src.agents.client.load_dotenv')
    @patch('src.agents.client.OpenAI')
    def test_current_provider_property(self, mock_openai_class, mock_load_dotenv, temp_config_file, mock_env_vars):
        """Test current_provider property."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        wrapper = AIClientWrapper(provider='gemini', config_path=temp_config_file)
        assert wrapper.current_provider == 'gemini'

    @patch('src.agents.client.load_dotenv')
    @patch('src.agents.client.OpenAI')
    def test_base_url_property(self, mock_openai_class, mock_load_dotenv, temp_config_file, mock_env_vars):
        """Test base_url property."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        wrapper = AIClientWrapper(provider='claude', config_path=temp_config_file)
        assert wrapper.base_url == "https://api.anthropic.com/v1/"

    @patch('src.agents.client.load_dotenv')
    @patch('src.agents.client.OpenAI')
    def test_repr(self, mock_openai_class, mock_load_dotenv, temp_config_file, mock_env_vars):
        """Test string representation."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        wrapper = AIClientWrapper(provider='claude', config_path=temp_config_file)
        repr_str = repr(wrapper)

        assert 'claude' in repr_str
        assert 'claude-sonnet-4-5' in repr_str


class TestClientFactory:
    """Test suite for ClientFactory class."""

    def test_init(self, temp_config_file):
        """Test factory initialization."""
        factory = ClientFactory(temp_config_file)
        assert factory.config_path == factory.config_loader.config_path

    def test_get_available_providers(self, temp_config_file):
        """Test getting available providers."""
        factory = ClientFactory(temp_config_file)
        providers = factory.get_available_providers()

        assert 'claude' in providers
        assert 'gemini' in providers
        assert 'openai' in providers

    def test_get_all_models(self, temp_config_file):
        """Test getting all models."""
        factory = ClientFactory(temp_config_file)
        all_models = factory.get_all_models()

        assert 'claude' in all_models
        assert 'gemini' in all_models
        assert 'openai' in all_models
        assert 'claude-sonnet-4-5' in all_models['claude']
        assert 'gemini-3-flash-preview' in all_models['gemini']
        assert 'gpt-4o' in all_models['openai']

    @patch('src.agents.client.load_dotenv')
    @patch('src.agents.client.OpenAI')
    def test_create_client_default(self, mock_openai_class, mock_load_dotenv, temp_config_file, mock_env_vars):
        """Test creating client with default provider."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        factory = ClientFactory(temp_config_file)
        wrapper = factory.create_client()

        assert isinstance(wrapper, AIClientWrapper)
        assert wrapper.provider == 'claude'

    @patch('src.agents.client.load_dotenv')
    @patch('src.agents.client.OpenAI')
    def test_create_client_specific_provider(self, mock_openai_class, mock_load_dotenv, temp_config_file, mock_env_vars):
        """Test creating client with specific provider."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        factory = ClientFactory(temp_config_file)
        wrapper = factory.create_client(provider='gemini')

        assert wrapper.provider == 'gemini'

    def test_create_client_invalid_provider(self, temp_config_file):
        """Test creating client with invalid provider."""
        factory = ClientFactory(temp_config_file)

        with pytest.raises(ValueError, match="Provider 'invalid' not found"):
            factory.create_client(provider='invalid')

    @patch('src.agents.client.load_dotenv')
    @patch('src.agents.client.OpenAI')
    def test_create_all_clients(self, mock_openai_class, mock_load_dotenv, temp_config_file, mock_env_vars):
        """Test creating clients for all providers."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        factory = ClientFactory(temp_config_file)
        clients = factory.create_all_clients()

        assert 'claude' in clients
        assert 'gemini' in clients
        assert 'openai' in clients
        assert isinstance(clients['claude'], AIClientWrapper)
        assert isinstance(clients['gemini'], AIClientWrapper)
        assert isinstance(clients['openai'], AIClientWrapper)

    @patch('src.agents.client.load_dotenv')
    @patch('src.agents.client.OpenAI')
    def test_create_all_clients_with_failure(self, mock_openai_class, mock_load_dotenv, temp_config_file, monkeypatch, capsys):
        """Test creating all clients when one fails."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # Remove one API key to cause failure
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "mock-key")
        monkeypatch.setenv("OPENAI_API_KEY", "mock-key")

        factory = ClientFactory(temp_config_file)
        clients = factory.create_all_clients()

        # Should have successfully created clients for the other providers
        assert 'claude' in clients or 'openai' in clients

        # Check that warning was printed
        captured = capsys.readouterr()
        assert "Warning" in captured.out or "gemini" in captured.out.lower()

    @patch('src.agents.client.load_dotenv')
    @patch('src.agents.client.OpenAI')
    def test_create_client_for_model(self, mock_openai_class, mock_load_dotenv, temp_config_file, mock_env_vars):
        """Test creating client based on model name."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        factory = ClientFactory(temp_config_file)
        wrapper = factory.create_client_for_model('claude-opus-4')

        assert wrapper.provider == 'claude'

    @patch('src.agents.client.load_dotenv')
    @patch('src.agents.client.OpenAI')
    def test_create_client_for_model_gemini(self, mock_openai_class, mock_load_dotenv, temp_config_file, mock_env_vars):
        """Test creating client for Gemini model."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        factory = ClientFactory(temp_config_file)
        wrapper = factory.create_client_for_model('gemini-3-flash-preview')

        assert wrapper.provider == 'gemini'

    def test_create_client_for_invalid_model(self, temp_config_file):
        """Test creating client for non-existent model."""
        factory = ClientFactory(temp_config_file)

        with pytest.raises(ValueError, match="Model 'invalid-model' not found"):
            factory.create_client_for_model('invalid-model')

    def test_get_provider_for_model(self, temp_config_file):
        """Test getting provider for a specific model."""
        factory = ClientFactory(temp_config_file)

        assert factory.get_provider_for_model('claude-sonnet-4-5') == 'claude'
        assert factory.get_provider_for_model('gemini-3-flash-preview') == 'gemini'
        assert factory.get_provider_for_model('gpt-4o') == 'openai'

    def test_get_provider_for_invalid_model(self, temp_config_file):
        """Test getting provider for non-existent model."""
        factory = ClientFactory(temp_config_file)
        result = factory.get_provider_for_model('invalid-model')

        assert result is None

    def test_repr(self, temp_config_file):
        """Test string representation."""
        factory = ClientFactory(temp_config_file)
        repr_str = repr(factory)

        assert 'ClientFactory' in repr_str
        assert 'claude' in repr_str
        assert 'gemini' in repr_str
        assert 'openai' in repr_str
