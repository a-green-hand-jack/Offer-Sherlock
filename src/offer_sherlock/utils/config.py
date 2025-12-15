"""Configuration management for Offer-Sherlock.

Uses pydantic-settings for type-safe configuration with environment variable support.
"""

from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    QWEN = "qwen"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM Provider Selection
    llm_provider: LLMProvider = Field(
        default=LLMProvider.OPENAI,
        description="Default LLM provider to use",
    )

    # OpenAI Configuration
    openai_api_key: Optional[SecretStr] = Field(
        default=None,
        description="OpenAI API key",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model to use",
    )
    openai_base_url: Optional[str] = Field(
        default=None,
        description="Custom OpenAI API base URL (for proxies or compatible APIs)",
    )

    # Anthropic (Claude) Configuration
    anthropic_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Anthropic API key",
    )
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Anthropic model to use",
    )

    # Google (Gemini) Configuration
    google_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Google AI API key",
    )
    google_model: str = Field(
        default="gemini-1.5-flash",
        description="Google model to use",
    )

    # Qwen (Alibaba DashScope) Configuration
    dashscope_api_key: Optional[SecretStr] = Field(
        default=None,
        description="Alibaba DashScope API key for Qwen models",
    )
    qwen_model: str = Field(
        default="qwen-plus",
        description="Qwen model to use (qwen-turbo, qwen-plus, qwen-max)",
    )

    # LLM Common Settings
    llm_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Temperature for LLM responses (0.0 = deterministic)",
    )
    llm_max_tokens: int = Field(
        default=4096,
        description="Maximum tokens for LLM responses",
    )

    # Database Configuration
    database_url: str = Field(
        default="sqlite:///./data/offers.db",
        description="Database connection URL",
    )

    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level",
    )

    def get_api_key(self, provider: Optional[LLMProvider] = None) -> Optional[str]:
        """Get the API key for a specific provider.

        Args:
            provider: The LLM provider. If None, uses the default provider.

        Returns:
            The API key as a string, or None if not configured.
        """
        provider = provider or self.llm_provider
        key_map = {
            LLMProvider.OPENAI: self.openai_api_key,
            LLMProvider.ANTHROPIC: self.anthropic_api_key,
            LLMProvider.GOOGLE: self.google_api_key,
            LLMProvider.QWEN: self.dashscope_api_key,
        }
        secret = key_map.get(provider)
        return secret.get_secret_value() if secret else None

    def get_model_name(self, provider: Optional[LLMProvider] = None) -> str:
        """Get the model name for a specific provider.

        Args:
            provider: The LLM provider. If None, uses the default provider.

        Returns:
            The model name string.
        """
        provider = provider or self.llm_provider
        model_map = {
            LLMProvider.OPENAI: self.openai_model,
            LLMProvider.ANTHROPIC: self.anthropic_model,
            LLMProvider.GOOGLE: self.google_model,
            LLMProvider.QWEN: self.qwen_model,
        }
        return model_map.get(provider, self.openai_model)


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings.

    Returns:
        Settings instance loaded from environment.
    """
    return Settings()
