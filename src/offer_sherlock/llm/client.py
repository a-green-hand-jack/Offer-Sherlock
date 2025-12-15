"""LLM Client - Unified interface for multiple LLM providers.

Supports:
- OpenAI (GPT-4o, GPT-4o-mini, etc.)
- Anthropic (Claude 3.5 Sonnet, etc.)
- Google (Gemini 1.5 Pro/Flash)
- Qwen (via DashScope - qwen-turbo, qwen-plus, qwen-max)
"""

from typing import Any, Optional, Type, TypeVar

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel

from offer_sherlock.utils.config import LLMProvider, Settings, get_settings

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Unified LLM client supporting multiple providers.

    Example usage:
        >>> client = LLMClient()  # Uses default provider from settings
        >>> response = client.chat("Hello, world!")

        >>> # With structured output
        >>> from pydantic import BaseModel
        >>> class Person(BaseModel):
        ...     name: str
        ...     age: int
        >>> person = client.chat_structured(
        ...     "Extract: John is 30 years old",
        ...     output_schema=Person
        ... )

        >>> # Switch provider at runtime
        >>> client = LLMClient(provider=LLMProvider.ANTHROPIC)
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        settings: Optional[Settings] = None,
    ):
        """Initialize the LLM client.

        Args:
            provider: LLM provider to use. Defaults to settings.llm_provider.
            model: Model name to use. Defaults to provider's default model.
            temperature: Temperature for responses. Defaults to settings.llm_temperature.
            max_tokens: Max tokens for responses. Defaults to settings.llm_max_tokens.
            settings: Settings instance. Defaults to get_settings().
        """
        self._settings = settings or get_settings()
        self._provider = provider or self._settings.llm_provider
        self._model = model or self._settings.get_model_name(self._provider)
        self._temperature = (
            temperature if temperature is not None else self._settings.llm_temperature
        )
        self._max_tokens = max_tokens or self._settings.llm_max_tokens
        self._llm: Optional[BaseChatModel] = None

    @property
    def provider(self) -> LLMProvider:
        """Get the current LLM provider."""
        return self._provider

    @property
    def model(self) -> str:
        """Get the current model name."""
        return self._model

    @property
    def llm(self) -> BaseChatModel:
        """Get the LangChain LLM instance (lazy initialization)."""
        if self._llm is None:
            self._llm = self._create_llm()
        return self._llm

    def _create_llm(self) -> BaseChatModel:
        """Create the appropriate LangChain LLM based on provider.

        Returns:
            Configured BaseChatModel instance.

        Raises:
            ValueError: If API key is not configured or provider is unsupported.
        """
        api_key = self._settings.get_api_key(self._provider)
        if not api_key:
            raise ValueError(
                f"API key not configured for provider: {self._provider.value}. "
                f"Please set the corresponding environment variable."
            )

        if self._provider == LLMProvider.OPENAI:
            return self._create_openai_llm(api_key)
        elif self._provider == LLMProvider.ANTHROPIC:
            return self._create_anthropic_llm(api_key)
        elif self._provider == LLMProvider.GOOGLE:
            return self._create_google_llm(api_key)
        elif self._provider == LLMProvider.QWEN:
            return self._create_qwen_llm(api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {self._provider}")

    def _create_openai_llm(self, api_key: str) -> BaseChatModel:
        """Create OpenAI LLM instance."""
        from langchain_openai import ChatOpenAI

        kwargs: dict[str, Any] = {
            "model": self._model,
            "api_key": api_key,
            "temperature": self._temperature,
            "max_tokens": self._max_tokens,
        }
        if self._settings.openai_base_url:
            kwargs["base_url"] = self._settings.openai_base_url

        return ChatOpenAI(**kwargs)

    def _create_anthropic_llm(self, api_key: str) -> BaseChatModel:
        """Create Anthropic (Claude) LLM instance."""
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=self._model,
            api_key=api_key,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )

    def _create_google_llm(self, api_key: str) -> BaseChatModel:
        """Create Google (Gemini) LLM instance."""
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=self._model,
            google_api_key=api_key,
            temperature=self._temperature,
            max_output_tokens=self._max_tokens,
        )

    def _create_qwen_llm(self, api_key: str) -> BaseChatModel:
        """Create Qwen (DashScope) LLM instance."""
        from langchain_community.chat_models import ChatTongyi

        return ChatTongyi(
            model=self._model,
            dashscope_api_key=api_key,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
        )

    def chat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Send a chat message and get a response.

        Args:
            message: The user message.
            system_prompt: Optional system prompt to set context.

        Returns:
            The LLM's response as a string.
        """
        messages: list[BaseMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=message))

        response = self.llm.invoke(messages)
        return str(response.content)

    def chat_structured(
        self,
        message: str,
        output_schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        """Send a chat message and get a structured response.

        Uses LangChain's with_structured_output for providers that support it,
        or falls back to PydanticOutputParser.

        Args:
            message: The user message.
            output_schema: Pydantic model class for the expected output.
            system_prompt: Optional system prompt to set context.

        Returns:
            Parsed response as the specified Pydantic model.
        """
        # Try to use native structured output if available
        if hasattr(self.llm, "with_structured_output"):
            structured_llm = self.llm.with_structured_output(output_schema)
            messages: list[BaseMessage] = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=message))
            return structured_llm.invoke(messages)

        # Fallback to PydanticOutputParser
        parser = PydanticOutputParser(pydantic_object=output_schema)
        format_instructions = parser.get_format_instructions()

        full_message = f"{message}\n\n{format_instructions}"
        response = self.chat(full_message, system_prompt)
        return parser.parse(response)

    async def achat(
        self,
        message: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Async version of chat.

        Args:
            message: The user message.
            system_prompt: Optional system prompt to set context.

        Returns:
            The LLM's response as a string.
        """
        messages: list[BaseMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=message))

        response = await self.llm.ainvoke(messages)
        return str(response.content)

    async def achat_structured(
        self,
        message: str,
        output_schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        """Async version of chat_structured.

        Args:
            message: The user message.
            output_schema: Pydantic model class for the expected output.
            system_prompt: Optional system prompt to set context.

        Returns:
            Parsed response as the specified Pydantic model.
        """
        if hasattr(self.llm, "with_structured_output"):
            structured_llm = self.llm.with_structured_output(output_schema)
            messages: list[BaseMessage] = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=message))
            return await structured_llm.ainvoke(messages)

        parser = PydanticOutputParser(pydantic_object=output_schema)
        format_instructions = parser.get_format_instructions()

        full_message = f"{message}\n\n{format_instructions}"
        response = await self.achat(full_message, system_prompt)
        return parser.parse(response)

    def __repr__(self) -> str:
        return f"LLMClient(provider={self._provider.value}, model={self._model})"
