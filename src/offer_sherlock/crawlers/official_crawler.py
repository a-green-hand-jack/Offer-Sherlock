"""Official job site crawler using Crawl4AI.

This module provides a crawler optimized for scraping official company
career pages and extracting job descriptions in LLM-friendly markdown format.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

from offer_sherlock.crawlers.base import BaseCrawler, CrawlResult


@dataclass
class CrawlTarget:
    """Configuration for a crawl target.

    Attributes:
        url: The URL to crawl.
        company: Company name for this target.
        css_selector: Optional CSS selector to extract specific content.
        wait_for: Optional wait condition (CSS selector or JS function).
        js_code: Optional JavaScript to execute before extraction.
    """

    url: str
    company: str
    css_selector: Optional[str] = None
    wait_for: Optional[str] = None
    js_code: Optional[str] = None
    metadata: dict = field(default_factory=dict)


class OfficialCrawler(BaseCrawler):
    """Crawler for official company career pages using Crawl4AI.

    This crawler uses Crawl4AI to render JavaScript-heavy career pages
    and extract clean markdown content suitable for LLM processing.

    Example:
        >>> crawler = OfficialCrawler()
        >>> result = await crawler.crawl("https://jobs.bytedance.com/...")
        >>> print(result.markdown)

        >>> # With CSS selector for specific content
        >>> result = await crawler.crawl(
        ...     "https://jobs.bytedance.com/...",
        ...     css_selector=".job-detail"
        ... )
    """

    def __init__(
        self,
        headless: bool = True,
        verbose: bool = False,
        use_cache: bool = True,
    ):
        """Initialize the crawler.

        Args:
            headless: Run browser in headless mode.
            verbose: Enable verbose logging.
            use_cache: Enable caching of crawled pages.
        """
        self.headless = headless
        self.verbose = verbose
        self.use_cache = use_cache
        self._browser_config = BrowserConfig(
            headless=headless,
            verbose=verbose,
        )

    async def crawl(
        self,
        url: str,
        css_selector: Optional[str] = None,
        wait_for: Optional[str] = None,
        js_code: Optional[str] = None,
        timeout: int = 30000,
        **kwargs,
    ) -> CrawlResult:
        """Crawl a single URL and extract markdown content.

        Args:
            url: The URL to crawl.
            css_selector: CSS selector to extract specific content.
                         If None, extracts entire page.
            wait_for: Wait condition before extraction.
                     Can be CSS selector (e.g., "css:.job-list")
                     or JS function (e.g., "js:() => document.querySelector('.loaded')")
            js_code: JavaScript code to execute before extraction.
            timeout: Page load timeout in milliseconds.
            **kwargs: Additional options passed to CrawlerRunConfig.

        Returns:
            CrawlResult with extracted markdown content.
        """
        # Build run configuration
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.ENABLED if self.use_cache else CacheMode.BYPASS,
            css_selector=css_selector,
            wait_for=wait_for,
            js_code=js_code,
            page_timeout=timeout,
            **kwargs,
        )

        try:
            async with AsyncWebCrawler(config=self._browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)

                if result.success:
                    return CrawlResult(
                        url=url,
                        markdown=result.markdown or "",
                        html=result.html,
                        title=result.metadata.get("title") if result.metadata else None,
                        success=True,
                        metadata={
                            "status_code": result.status_code if hasattr(result, 'status_code') else None,
                            "links_count": len(result.links) if hasattr(result, 'links') and result.links else 0,
                        },
                    )
                else:
                    return CrawlResult(
                        url=url,
                        markdown="",
                        success=False,
                        error=result.error_message if hasattr(result, 'error_message') else "Unknown error",
                    )

        except Exception as e:
            return CrawlResult(
                url=url,
                markdown="",
                success=False,
                error=str(e),
            )

    async def crawl_many(
        self,
        urls: list[str],
        css_selector: Optional[str] = None,
        **kwargs,
    ) -> list[CrawlResult]:
        """Crawl multiple URLs concurrently.

        Args:
            urls: List of URLs to crawl.
            css_selector: CSS selector applied to all URLs.
            **kwargs: Additional options passed to crawl().

        Returns:
            List of CrawlResult for each URL.
        """
        tasks = [
            self.crawl(url, css_selector=css_selector, **kwargs)
            for url in urls
        ]
        return await asyncio.gather(*tasks)

    async def crawl_target(self, target: CrawlTarget) -> CrawlResult:
        """Crawl a configured target.

        Args:
            target: CrawlTarget with URL and configuration.

        Returns:
            CrawlResult with extracted content.
        """
        result = await self.crawl(
            url=target.url,
            css_selector=target.css_selector,
            wait_for=target.wait_for,
            js_code=target.js_code,
        )
        # Add target metadata to result
        if result.metadata is None:
            result.metadata = {}
        result.metadata["company"] = target.company
        result.metadata.update(target.metadata)
        return result

    async def crawl_targets(self, targets: list[CrawlTarget]) -> list[CrawlResult]:
        """Crawl multiple configured targets.

        Args:
            targets: List of CrawlTarget configurations.

        Returns:
            List of CrawlResult for each target.
        """
        tasks = [self.crawl_target(target) for target in targets]
        return await asyncio.gather(*tasks)
