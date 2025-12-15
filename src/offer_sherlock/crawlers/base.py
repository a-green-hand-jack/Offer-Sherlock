"""Base crawler interface for Offer-Sherlock."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class CrawlResult:
    """Result from a web crawl operation.

    Attributes:
        url: The URL that was crawled.
        markdown: Clean markdown content extracted from the page.
        html: Raw HTML content (optional).
        title: Page title if available.
        success: Whether the crawl was successful.
        error: Error message if crawl failed.
        crawled_at: Timestamp of the crawl.
        metadata: Additional metadata from the crawl.
    """

    url: str
    markdown: str
    html: Optional[str] = None
    title: Optional[str] = None
    success: bool = True
    error: Optional[str] = None
    crawled_at: datetime = None
    metadata: Optional[dict] = None

    def __post_init__(self):
        if self.crawled_at is None:
            self.crawled_at = datetime.now()


class BaseCrawler(ABC):
    """Abstract base class for web crawlers.

    All crawler implementations should inherit from this class
    and implement the abstract methods.
    """

    @abstractmethod
    async def crawl(self, url: str, **kwargs) -> CrawlResult:
        """Crawl a single URL and return the result.

        Args:
            url: The URL to crawl.
            **kwargs: Additional crawler-specific options.

        Returns:
            CrawlResult containing the extracted content.
        """
        pass

    @abstractmethod
    async def crawl_many(self, urls: list[str], **kwargs) -> list[CrawlResult]:
        """Crawl multiple URLs.

        Args:
            urls: List of URLs to crawl.
            **kwargs: Additional crawler-specific options.

        Returns:
            List of CrawlResult for each URL.
        """
        pass
