"""Tests for OfficialCrawler."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from offer_sherlock.crawlers import OfficialCrawler, CrawlTarget, CrawlResult


class TestCrawlResult:
    """Tests for CrawlResult dataclass."""

    def test_crawl_result_creation(self):
        """Test basic CrawlResult creation."""
        result = CrawlResult(
            url="https://example.com",
            markdown="# Test",
            success=True,
        )
        assert result.url == "https://example.com"
        assert result.markdown == "# Test"
        assert result.success is True
        assert result.crawled_at is not None
        assert isinstance(result.crawled_at, datetime)

    def test_crawl_result_with_error(self):
        """Test CrawlResult with error."""
        result = CrawlResult(
            url="https://example.com",
            markdown="",
            success=False,
            error="Connection timeout",
        )
        assert result.success is False
        assert result.error == "Connection timeout"

    def test_crawl_result_with_metadata(self):
        """Test CrawlResult with metadata."""
        result = CrawlResult(
            url="https://example.com",
            markdown="# Test",
            success=True,
            metadata={"company": "TestCorp", "status_code": 200},
        )
        assert result.metadata["company"] == "TestCorp"
        assert result.metadata["status_code"] == 200


class TestCrawlTarget:
    """Tests for CrawlTarget dataclass."""

    def test_crawl_target_basic(self):
        """Test basic CrawlTarget creation."""
        target = CrawlTarget(
            url="https://jobs.example.com",
            company="Example Corp",
        )
        assert target.url == "https://jobs.example.com"
        assert target.company == "Example Corp"
        assert target.css_selector is None
        assert target.metadata == {}

    def test_crawl_target_with_options(self):
        """Test CrawlTarget with all options."""
        target = CrawlTarget(
            url="https://jobs.example.com",
            company="Example Corp",
            css_selector=".job-list",
            wait_for="css:.job-item",
            js_code="window.scrollTo(0, 1000);",
            metadata={"type": "campus"},
        )
        assert target.css_selector == ".job-list"
        assert target.wait_for == "css:.job-item"
        assert target.js_code == "window.scrollTo(0, 1000);"
        assert target.metadata["type"] == "campus"


class TestOfficialCrawler:
    """Tests for OfficialCrawler."""

    def test_crawler_initialization(self):
        """Test crawler initialization with default options."""
        crawler = OfficialCrawler()
        assert crawler.headless is True
        assert crawler.verbose is False
        assert crawler.use_cache is True

    def test_crawler_initialization_custom(self):
        """Test crawler initialization with custom options."""
        crawler = OfficialCrawler(
            headless=False,
            verbose=True,
            use_cache=False,
        )
        assert crawler.headless is False
        assert crawler.verbose is True
        assert crawler.use_cache is False

    @pytest.mark.asyncio
    async def test_crawl_returns_result(self):
        """Test that crawl returns a CrawlResult."""
        crawler = OfficialCrawler()

        # Mock the AsyncWebCrawler
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown = "# Test Page\nContent here"
        mock_result.html = "<html><body>Test</body></html>"
        mock_result.metadata = {"title": "Test Page"}
        mock_result.status_code = 200
        mock_result.links = []

        with patch("offer_sherlock.crawlers.official_crawler.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun = AsyncMock(return_value=mock_result)
            mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
            mock_crawler.__aexit__ = AsyncMock(return_value=None)
            mock_crawler_class.return_value = mock_crawler

            result = await crawler.crawl("https://example.com")

            assert isinstance(result, CrawlResult)
            assert result.success is True
            assert result.markdown == "# Test Page\nContent here"
            assert result.url == "https://example.com"

    @pytest.mark.asyncio
    async def test_crawl_handles_failure(self):
        """Test that crawl handles failures gracefully."""
        crawler = OfficialCrawler()

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.markdown = None
        mock_result.error_message = "Page not found"

        with patch("offer_sherlock.crawlers.official_crawler.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun = AsyncMock(return_value=mock_result)
            mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
            mock_crawler.__aexit__ = AsyncMock(return_value=None)
            mock_crawler_class.return_value = mock_crawler

            result = await crawler.crawl("https://example.com/notfound")

            assert result.success is False
            assert result.error == "Page not found"

    @pytest.mark.asyncio
    async def test_crawl_handles_exception(self):
        """Test that crawl handles exceptions gracefully."""
        crawler = OfficialCrawler()

        with patch("offer_sherlock.crawlers.official_crawler.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.__aenter__ = AsyncMock(side_effect=Exception("Connection failed"))
            mock_crawler_class.return_value = mock_crawler

            result = await crawler.crawl("https://example.com")

            assert result.success is False
            assert "Connection failed" in result.error

    @pytest.mark.asyncio
    async def test_crawl_target(self):
        """Test crawl_target method."""
        crawler = OfficialCrawler()

        target = CrawlTarget(
            url="https://jobs.example.com",
            company="Example Corp",
            metadata={"type": "campus"},
        )

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown = "# Jobs"
        mock_result.html = None
        mock_result.metadata = {}
        mock_result.status_code = 200
        mock_result.links = []

        with patch("offer_sherlock.crawlers.official_crawler.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun = AsyncMock(return_value=mock_result)
            mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
            mock_crawler.__aexit__ = AsyncMock(return_value=None)
            mock_crawler_class.return_value = mock_crawler

            result = await crawler.crawl_target(target)

            assert result.success is True
            assert result.metadata["company"] == "Example Corp"
            assert result.metadata["type"] == "campus"

    @pytest.mark.asyncio
    async def test_crawl_many(self):
        """Test crawl_many method."""
        crawler = OfficialCrawler()

        urls = ["https://example1.com", "https://example2.com"]

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown = "# Test"
        mock_result.html = None
        mock_result.metadata = {}
        mock_result.status_code = 200
        mock_result.links = []

        with patch("offer_sherlock.crawlers.official_crawler.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun = AsyncMock(return_value=mock_result)
            mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
            mock_crawler.__aexit__ = AsyncMock(return_value=None)
            mock_crawler_class.return_value = mock_crawler

            results = await crawler.crawl_many(urls)

            assert len(results) == 2
            assert all(r.success for r in results)
