"""LLM module - Unified interface for multiple LLM providers.

Supported providers:
- OpenAI (GPT-4o, GPT-4o-mini)
- Anthropic (Claude 3.5 Sonnet)
- Google (Gemini 1.5 Pro/Flash)
- Qwen (qwen-turbo, qwen-plus, qwen-max)

Example:
    >>> from offer_sherlock.llm import LLMClient, LLMProvider
    >>> client = LLMClient()  # Uses default from env
    >>> response = client.chat("Hello!")

    >>> # Use specific provider
    >>> client = LLMClient(provider=LLMProvider.ANTHROPIC)
    >>> response = client.chat("Hello from Claude!")
"""

from offer_sherlock.llm.client import LLMClient
from offer_sherlock.utils.config import LLMProvider

__all__ = ["LLMClient", "LLMProvider"]
