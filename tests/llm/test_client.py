"""Tests for LLM Client."""

import os
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from offer_sherlock.llm import LLMClient, LLMProvider
from offer_sherlock.utils.config import Settings


class SampleOutput(BaseModel):
    """Sample output schema for testing structured output."""

    name: str
    age: int


@pytest.fixture(autouse=True)
def clear_settings_cache():
    """Clear settings cache before and after each test."""
    from offer_sherlock.utils.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


class TestLLMClientInit:
    """Tests for LLMClient initialization."""

    def test_default_provider_from_settings(self):
        """Test that default provider comes from settings."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "anthropic"}, clear=False):
            client = LLMClient()
            assert client.provider == LLMProvider.ANTHROPIC

    def test_explicit_provider_override(self):
        """Test that explicit provider overrides settings."""
        client = LLMClient(provider=LLMProvider.GOOGLE)
        assert client.provider == LLMProvider.GOOGLE

    def test_explicit_model_override(self):
        """Test that explicit model overrides default."""
        client = LLMClient(provider=LLMProvider.OPENAI, model="gpt-4")
        assert client.model == "gpt-4"

    def test_repr(self):
        """Test string representation."""
        client = LLMClient(provider=LLMProvider.OPENAI, model="gpt-4o-mini")
        assert "openai" in repr(client)
        assert "gpt-4o-mini" in repr(client)

    def test_temperature_override(self):
        """Test temperature override."""
        client = LLMClient(provider=LLMProvider.OPENAI, temperature=0.8)
        assert client._temperature == 0.8

    def test_max_tokens_override(self):
        """Test max_tokens override."""
        client = LLMClient(provider=LLMProvider.OPENAI, max_tokens=2048)
        assert client._max_tokens == 2048


class TestLLMClientProviders:
    """Tests for different LLM provider creation."""

    def test_missing_api_key_raises_error(self):
        """Test that missing API key raises ValueError."""
        # Clear all API keys
        env_without_keys = {
            k: v for k, v in os.environ.items()
            if not k.endswith("_API_KEY") and k != "DASHSCOPE_API_KEY"
        }
        with patch.dict(os.environ, env_without_keys, clear=True):
            client = LLMClient(provider=LLMProvider.OPENAI)
            with pytest.raises(ValueError, match="API key not configured"):
                _ = client.llm

    def test_openai_client_initialization(self):
        """Test OpenAI client can be initialized with API key."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False):
            client = LLMClient(provider=LLMProvider.OPENAI)
            # Just verify the client was created without error
            assert client.provider == LLMProvider.OPENAI
            assert client.model == "gpt-4o-mini"  # default model

    def test_anthropic_client_initialization(self):
        """Test Anthropic client can be initialized with API key."""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}, clear=False):
            client = LLMClient(provider=LLMProvider.ANTHROPIC)
            assert client.provider == LLMProvider.ANTHROPIC

    def test_google_client_initialization(self):
        """Test Google client can be initialized with API key."""
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "test-key"}, clear=False):
            client = LLMClient(provider=LLMProvider.GOOGLE)
            assert client.provider == LLMProvider.GOOGLE

    def test_qwen_client_initialization(self):
        """Test Qwen client can be initialized with API key."""
        with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "test-key"}, clear=False):
            client = LLMClient(provider=LLMProvider.QWEN)
            assert client.provider == LLMProvider.QWEN


class TestLLMClientChatMocked:
    """Tests for LLM chat functionality with mocked LLM."""

    def test_chat_simple(self):
        """Test simple chat without system prompt."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="Hello!")

        client = LLMClient(provider=LLMProvider.OPENAI)
        client._llm = mock_llm  # Inject mock

        response = client.chat("Hi there")

        assert response == "Hello!"
        mock_llm.invoke.assert_called_once()

    def test_chat_with_system_prompt(self):
        """Test chat with system prompt."""
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="I am a helpful assistant.")

        client = LLMClient(provider=LLMProvider.OPENAI)
        client._llm = mock_llm

        response = client.chat("Who are you?", system_prompt="You are a helpful assistant.")

        assert response == "I am a helpful assistant."
        call_args = mock_llm.invoke.call_args[0][0]
        assert len(call_args) == 2  # SystemMessage + HumanMessage

    def test_chat_structured(self):
        """Test structured output chat."""
        mock_llm = MagicMock()
        mock_structured_llm = MagicMock()
        mock_structured_llm.invoke.return_value = SampleOutput(name="John", age=30)
        mock_llm.with_structured_output.return_value = mock_structured_llm

        client = LLMClient(provider=LLMProvider.OPENAI)
        client._llm = mock_llm

        result = client.chat_structured(
            "Extract: John is 30 years old", output_schema=SampleOutput
        )

        assert isinstance(result, SampleOutput)
        assert result.name == "John"
        assert result.age == 30


class TestSettings:
    """Tests for Settings configuration."""

    def test_default_settings(self):
        """Test default settings values."""
        with patch.dict(os.environ, {}, clear=True):
            from offer_sherlock.utils.config import get_settings

            get_settings.cache_clear()

            settings = Settings()
            assert settings.llm_provider == LLMProvider.OPENAI
            assert settings.llm_temperature == 0.0
            assert settings.openai_model == "gpt-4o-mini"

            get_settings.cache_clear()

    def test_settings_from_env(self):
        """Test settings loaded from environment."""
        env_vars = {
            "LLM_PROVIDER": "anthropic",
            "LLM_TEMPERATURE": "0.7",
            "ANTHROPIC_MODEL": "claude-3-opus-20240229",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            from offer_sherlock.utils.config import get_settings

            get_settings.cache_clear()

            settings = Settings()
            assert settings.llm_provider == LLMProvider.ANTHROPIC
            assert settings.llm_temperature == 0.7
            assert settings.anthropic_model == "claude-3-opus-20240229"

            get_settings.cache_clear()

    def test_get_api_key(self):
        """Test get_api_key method."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "openai-key",
                "ANTHROPIC_API_KEY": "anthropic-key",
            },
            clear=False,
        ):
            from offer_sherlock.utils.config import get_settings

            get_settings.cache_clear()

            settings = Settings()
            assert settings.get_api_key(LLMProvider.OPENAI) == "openai-key"
            assert settings.get_api_key(LLMProvider.ANTHROPIC) == "anthropic-key"
            assert settings.get_api_key(LLMProvider.GOOGLE) is None

            get_settings.cache_clear()

    def test_get_model_name(self):
        """Test get_model_name method."""
        with patch.dict(
            os.environ,
            {
                "OPENAI_MODEL": "gpt-4",
                "QWEN_MODEL": "qwen-max",
            },
            clear=False,
        ):
            from offer_sherlock.utils.config import get_settings

            get_settings.cache_clear()

            settings = Settings()
            assert settings.get_model_name(LLMProvider.OPENAI) == "gpt-4"
            assert settings.get_model_name(LLMProvider.QWEN) == "qwen-max"

            get_settings.cache_clear()
