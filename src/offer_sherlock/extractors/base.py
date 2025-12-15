"""Base extractor interface for LLM-powered data extraction."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from pydantic import BaseModel

from offer_sherlock.llm.client import LLMClient

T = TypeVar("T", bound=BaseModel)


class BaseExtractor(ABC, Generic[T]):
    """Abstract base class for LLM-powered data extractors.

    All extractor implementations should inherit from this class
    and implement the extract method.

    Attributes:
        llm: The LLM client used for extraction.
        max_content_length: Maximum content length to process (truncate if longer).
    """

    def __init__(
        self,
        llm_client: LLMClient,
        max_content_length: int = 15000,
    ):
        """Initialize the extractor.

        Args:
            llm_client: LLM client for structured extraction.
            max_content_length: Max characters to send to LLM (default 15000).
        """
        self.llm = llm_client
        self.max_content_length = max_content_length

    def _truncate_content(self, content: str) -> str:
        """Truncate content if it exceeds max length.

        Args:
            content: The content to potentially truncate.

        Returns:
            Truncated content with indicator if truncated.
        """
        if len(content) <= self.max_content_length:
            return content

        truncated = content[: self.max_content_length]
        return truncated + "\n\n[... 内容已截断 ...]"

    @abstractmethod
    async def extract(self, content: str, **kwargs) -> T:
        """Extract structured data from content.

        Args:
            content: Raw content to extract from.
            **kwargs: Additional extraction parameters.

        Returns:
            Extracted structured data.
        """
        pass
