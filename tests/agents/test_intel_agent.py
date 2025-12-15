"""Tests for IntelAgent."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from offer_sherlock.agents.intel_agent import AgentResult, IntelAgent
from offer_sherlock.database import DatabaseManager
from offer_sherlock.schemas.job import JobPosting, JobListExtraction
from offer_sherlock.schemas.insight import InsightSummary, Sentiment
from offer_sherlock.crawlers.base import CrawlResult


class TestAgentResult:
    """Tests for AgentResult dataclass."""

    def test_create_default(self):
        """Test creating AgentResult with defaults."""
        result = AgentResult(company="TestCorp")
        assert result.company == "TestCorp"
        assert result.success is True
        assert result.jobs_added == 0
        assert result.errors == []

    def test_create_with_values(self):
        """Test creating AgentResult with values."""
        result = AgentResult(
            company="字节跳动",
            success=True,
            jobs_found=10,
            jobs_added=5,
            jobs_updated=3,
            insight_generated=True,
            insight_sentiment="positive",
            posts_analyzed=8,
            duration_seconds=12.5,
        )
        assert result.jobs_found == 10
        assert result.insight_sentiment == "positive"

    def test_str_representation_success(self):
        """Test string representation for successful result."""
        result = AgentResult(
            company="腾讯",
            success=True,
            jobs_found=5,
            jobs_added=3,
            insight_generated=True,
            insight_sentiment="positive",
            duration_seconds=8.2,
        )
        s = str(result)
        assert "✅" in s
        assert "腾讯" in s
        assert "3 new jobs" in s
        assert "positive" in s

    def test_str_representation_failure(self):
        """Test string representation for failed result."""
        result = AgentResult(
            company="阿里",
            success=False,
            errors=["Error 1", "Error 2"],
            duration_seconds=5.0,
        )
        s = str(result)
        assert "❌" in s
        assert "errors=2" in s

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = AgentResult(
            company="美团",
            jobs_added=10,
            insight_generated=True,
        )
        d = result.to_dict()
        assert d["company"] == "美团"
        assert d["jobs_added"] == 10
        assert d["insight_generated"] is True


class TestIntelAgent:
    """Tests for IntelAgent."""

    @pytest.fixture
    def db(self):
        """Create in-memory database."""
        manager = DatabaseManager(db_path=":memory:")
        manager.create_tables()
        return manager

    @pytest.fixture
    def agent(self, db):
        """Create agent with mock extractors."""
        return IntelAgent(db)

    def test_init(self, db):
        """Test agent initialization."""
        agent = IntelAgent(db)
        assert agent.db == db
        assert agent._llm_client is None  # Lazy init

    def test_default_social_keywords(self, agent):
        """Test default social keyword generation."""
        keywords = agent._get_social_keywords("字节跳动")
        assert "字节跳动 offer" in keywords
        assert "字节跳动 面经" in keywords

    @pytest.mark.asyncio
    async def test_run_skip_all(self, agent):
        """Test run with both crawls skipped."""
        result = await agent.run(
            company="TestCorp",
            skip_official=True,
            skip_social=True,
        )
        assert result.company == "TestCorp"
        assert result.success is True
        assert result.jobs_added == 0
        assert result.insight_generated is False

    @pytest.mark.asyncio
    async def test_crawl_official_success(self, agent, db):
        """Test successful official site crawling."""
        # Mock the crawler and extractor
        mock_crawl_result = CrawlResult(
            url="https://test.com",
            markdown="# Jobs\n- Engineer",
            success=True,
        )

        mock_extraction = JobListExtraction(
            jobs=[
                JobPosting(
                    title="Engineer",
                    company="TestCorp",
                    job_id_external="JOB001",
                ),
                JobPosting(
                    title="Designer",
                    company="TestCorp",
                    job_id_external="JOB002",
                ),
            ],
            source_url="https://test.com",
        )

        # Create mock extractor
        mock_extractor = MagicMock()
        mock_extractor.extract = AsyncMock(return_value=mock_extraction)
        agent._job_extractor = mock_extractor

        with patch(
            "offer_sherlock.agents.intel_agent.OfficialCrawler"
        ) as MockCrawler:
            mock_crawler_instance = MagicMock()
            mock_crawler_instance.crawl = AsyncMock(return_value=mock_crawl_result)
            MockCrawler.return_value = mock_crawler_instance

            jobs_found, jobs_added, jobs_updated = await agent.crawl_official(
                company="TestCorp",
                url="https://test.com",
            )

        assert jobs_found == 2
        assert jobs_added == 2
        assert jobs_updated == 0

    @pytest.mark.asyncio
    async def test_crawl_social_success(self, agent, db):
        """Test successful social media crawling."""
        from offer_sherlock.crawlers.social_crawler import XhsNote

        mock_notes = [
            XhsNote(
                note_id="note1",
                title="面经分享",
                content="面试体验不错",
                user_nickname="user1",
                likes=100,
            ),
            XhsNote(
                note_id="note2",
                title="Offer 分享",
                content="薪资很好",
                user_nickname="user2",
                likes=200,
            ),
        ]

        mock_summary = InsightSummary(
            company="TestCorp",
            position_keyword="offer",
            overall_sentiment=Sentiment.POSITIVE,
            posts_analyzed=2,
        )

        # Create mock extractor
        mock_extractor = MagicMock()
        mock_extractor.analyze_notes = AsyncMock(return_value=mock_summary)
        agent._insight_extractor = mock_extractor

        with patch(
            "offer_sherlock.agents.intel_agent.XhsCrawler"
        ) as MockCrawler:
            mock_crawler_instance = AsyncMock()
            mock_crawler_instance.search = AsyncMock(return_value=mock_notes)
            mock_crawler_instance.__aenter__ = AsyncMock(
                return_value=mock_crawler_instance
            )
            mock_crawler_instance.__aexit__ = AsyncMock(return_value=None)
            MockCrawler.return_value = mock_crawler_instance

            summary = await agent.crawl_social(
                company="TestCorp",
                keywords=["TestCorp offer"],
            )

        assert summary is not None
        assert summary.overall_sentiment == Sentiment.POSITIVE

    @pytest.mark.asyncio
    async def test_run_handles_crawl_error(self, agent):
        """Test that run handles crawl errors gracefully."""
        with patch.object(
            agent, "crawl_official", new_callable=AsyncMock
        ) as mock_crawl:
            mock_crawl.side_effect = Exception("Network error")

            result = await agent.run(
                company="TestCorp",
                official_url="https://test.com",
                skip_social=True,
            )

        assert result.success is False
        assert len(result.errors) == 1
        assert "Network error" in result.errors[0]

    @pytest.mark.asyncio
    async def test_run_all_with_targets(self, agent, db):
        """Test batch run with crawl targets."""
        # Add some targets
        from offer_sherlock.database import CrawlTargetRepository

        with db.session() as session:
            repo = CrawlTargetRepository(session)
            repo.add("Company A", "https://a.com", is_active=True)
            repo.add("Company B", "https://b.com", is_active=True)
            repo.add("Company C", "https://c.com", is_active=False)  # Inactive

        # Mock the run method
        with patch.object(agent, "run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = AgentResult(company="Test", success=True)

            results = await agent.run_all(delay_between=0)

        # Should only run for active targets
        assert mock_run.call_count == 2
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_run_all_with_limit(self, agent, db):
        """Test batch run with max_companies limit."""
        from offer_sherlock.database import CrawlTargetRepository

        with db.session() as session:
            repo = CrawlTargetRepository(session)
            for i in range(5):
                repo.add(f"Company {i}", f"https://{i}.com", is_active=True)

        with patch.object(agent, "run", new_callable=AsyncMock) as mock_run:
            mock_run.return_value = AgentResult(company="Test", success=True)

            results = await agent.run_all(max_companies=2, delay_between=0)

        assert mock_run.call_count == 2
        assert len(results) == 2
