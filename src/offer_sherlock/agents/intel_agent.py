"""Intelligence Agent - Orchestrates the complete ETL pipeline.

This module provides the IntelAgent class that coordinates crawling,
extraction, and persistence of job postings and social intelligence.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from offer_sherlock.crawlers import OfficialCrawler, XhsCrawler
from offer_sherlock.database import (
    CrawlTargetRepository,
    DatabaseManager,
    InsightRepository,
    JobRepository,
)
from offer_sherlock.extractors import InsightExtractor, JobExtractor
from offer_sherlock.llm.client import LLMClient
from offer_sherlock.schemas.insight import InsightSummary
from offer_sherlock.utils.config import LLMProvider

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Result of an agent run for a single company.

    Attributes:
        company: Company name that was processed.
        success: Whether the overall run was successful.
        jobs_found: Total jobs found from crawling.
        jobs_added: New jobs added to database.
        jobs_updated: Existing jobs that were updated.
        insight_generated: Whether social insight was generated.
        insight_sentiment: Overall sentiment if insight was generated.
        posts_analyzed: Number of social posts analyzed.
        errors: List of error messages encountered.
        duration_seconds: Total time taken in seconds.
    """

    company: str
    success: bool = True
    jobs_found: int = 0
    jobs_added: int = 0
    jobs_updated: int = 0
    insight_generated: bool = False
    insight_sentiment: Optional[str] = None
    posts_analyzed: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def __str__(self) -> str:
        status = "✅" if self.success else "❌"
        parts = [f"{status} {self.company}:"]
        if self.jobs_found > 0:
            parts.append(f"{self.jobs_added} new jobs (of {self.jobs_found})")
        if self.insight_generated:
            parts.append(f"insight={self.insight_sentiment}")
        if self.errors:
            parts.append(f"errors={len(self.errors)}")
        parts.append(f"({self.duration_seconds:.1f}s)")
        return " | ".join(parts)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "company": self.company,
            "success": self.success,
            "jobs_found": self.jobs_found,
            "jobs_added": self.jobs_added,
            "jobs_updated": self.jobs_updated,
            "insight_generated": self.insight_generated,
            "insight_sentiment": self.insight_sentiment,
            "posts_analyzed": self.posts_analyzed,
            "errors": self.errors,
            "duration_seconds": self.duration_seconds,
        }


class IntelAgent:
    """Intelligence collection agent that orchestrates the ETL pipeline.

    Coordinates crawling of official job sites and social media,
    extraction of structured data using LLM, and persistence to database.

    Example:
        >>> db = DatabaseManager("data/offers.db")
        >>> db.create_tables()
        >>> agent = IntelAgent(db)
        >>>
        >>> # Single company
        >>> result = await agent.run("字节跳动", official_url="https://jobs.bytedance.com")
        >>> print(f"Added {result.jobs_added} jobs")
        >>>
        >>> # Batch mode
        >>> results = await agent.run_all()
    """

    # Default social media search keywords template
    DEFAULT_SOCIAL_KEYWORDS = ["{company} offer", "{company} 面经"]

    def __init__(
        self,
        db: DatabaseManager,
        llm_provider: LLMProvider = LLMProvider.QWEN,
        llm_model: str = "qwen-max",
        xhs_headless: bool = True,
    ):
        """Initialize the intelligence agent.

        Args:
            db: Database manager for persistence.
            llm_provider: LLM provider to use for extraction.
            llm_model: Model name for the LLM.
            xhs_headless: Whether to run XHS crawler in headless mode.
        """
        self.db = db
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.xhs_headless = xhs_headless

        # Lazy initialization
        self._llm_client: Optional[LLMClient] = None
        self._job_extractor: Optional[JobExtractor] = None
        self._insight_extractor: Optional[InsightExtractor] = None

    @property
    def llm_client(self) -> LLMClient:
        """Get LLM client (lazy initialization)."""
        if self._llm_client is None:
            self._llm_client = LLMClient(
                provider=self.llm_provider,
                model=self.llm_model,
            )
        return self._llm_client

    @property
    def job_extractor(self) -> JobExtractor:
        """Get job extractor (lazy initialization)."""
        if self._job_extractor is None:
            self._job_extractor = JobExtractor(llm_client=self.llm_client)
        return self._job_extractor

    @property
    def insight_extractor(self) -> InsightExtractor:
        """Get insight extractor (lazy initialization)."""
        if self._insight_extractor is None:
            self._insight_extractor = InsightExtractor(llm_client=self.llm_client)
        return self._insight_extractor

    async def run(
        self,
        company: str,
        official_url: Optional[str] = None,
        social_keywords: Optional[list[str]] = None,
        skip_official: bool = False,
        skip_social: bool = False,
        max_social_results: int = 10,
    ) -> AgentResult:
        """Run intelligence collection for a single company.

        Args:
            company: Company name to collect intelligence for.
            official_url: Official career page URL. If not provided,
                will try to find from CrawlTarget table.
            social_keywords: Keywords to search on social media.
                Defaults to ["{company} offer", "{company} 面经"].
            skip_official: Skip official site crawling.
            skip_social: Skip social media crawling.
            max_social_results: Max results per social keyword search.

        Returns:
            AgentResult with collection statistics.
        """
        start_time = time.time()
        result = AgentResult(company=company)

        logger.info(f"Starting intelligence collection for {company}")

        # Step 1: Crawl official site
        if not skip_official:
            url = official_url or self._get_official_url(company)
            if url:
                try:
                    jobs_found, jobs_added, jobs_updated = await self.crawl_official(
                        company, url
                    )
                    result.jobs_found = jobs_found
                    result.jobs_added = jobs_added
                    result.jobs_updated = jobs_updated
                    logger.info(
                        f"{company}: Found {jobs_found} jobs, "
                        f"added {jobs_added}, updated {jobs_updated}"
                    )
                except Exception as e:
                    error_msg = f"Official crawl failed: {str(e)}"
                    result.errors.append(error_msg)
                    logger.error(f"{company}: {error_msg}")
            else:
                logger.warning(f"{company}: No official URL found, skipping")

        # Step 2: Crawl social media
        if not skip_social:
            keywords = social_keywords or self._get_social_keywords(company)
            try:
                insight = await self.crawl_social(
                    company, keywords, max_results=max_social_results
                )
                if insight:
                    result.insight_generated = True
                    result.insight_sentiment = insight.overall_sentiment.value
                    result.posts_analyzed = insight.posts_analyzed
                    logger.info(
                        f"{company}: Generated insight from {insight.posts_analyzed} posts"
                    )
            except Exception as e:
                error_msg = f"Social crawl failed: {str(e)}"
                result.errors.append(error_msg)
                logger.error(f"{company}: {error_msg}")

        # Finalize
        result.duration_seconds = time.time() - start_time
        result.success = len(result.errors) == 0

        logger.info(f"Completed {company} in {result.duration_seconds:.1f}s")
        return result

    async def run_all(
        self,
        max_companies: Optional[int] = None,
        delay_between: float = 2.0,
    ) -> list[AgentResult]:
        """Run intelligence collection for all active crawl targets.

        Args:
            max_companies: Maximum number of companies to process.
            delay_between: Delay in seconds between companies (anti-scraping).

        Returns:
            List of AgentResult for each company.
        """
        results = []

        with self.db.session() as session:
            target_repo = CrawlTargetRepository(session)
            targets = target_repo.list_active()

            if max_companies:
                targets = targets[:max_companies]

            logger.info(f"Starting batch run for {len(targets)} companies")

            for i, target in enumerate(targets):
                if i > 0:
                    await asyncio.sleep(delay_between)

                result = await self.run(
                    company=target.company,
                    official_url=target.url,
                )
                results.append(result)

                # Update last crawled time
                target_repo.update_last_crawled(target.id)

        # Summary
        successful = sum(1 for r in results if r.success)
        total_jobs = sum(r.jobs_added for r in results)
        total_insights = sum(1 for r in results if r.insight_generated)

        logger.info(
            f"Batch run complete: {successful}/{len(results)} successful, "
            f"{total_jobs} jobs added, {total_insights} insights generated"
        )

        return results

    async def crawl_official(
        self,
        company: str,
        url: str,
    ) -> tuple[int, int, int]:
        """Crawl official career site and extract jobs.

        Args:
            company: Company name.
            url: Career page URL.

        Returns:
            Tuple of (jobs_found, jobs_added, jobs_updated).
        """
        logger.debug(f"Crawling official site: {url}")

        # Crawl (OfficialCrawler manages its own browser context internally)
        # Disable cache to ensure fresh content with proper JS rendering
        crawler = OfficialCrawler(use_cache=False)
        crawl_result = await crawler.crawl(url)

        if not crawl_result.success:
            raise RuntimeError(f"Crawl failed: {crawl_result.error}")

        # Extract
        extraction = await self.job_extractor.extract(
            content=crawl_result.markdown,
            company=company,
            source_url=url,
        )

        jobs_found = extraction.count
        if jobs_found == 0:
            logger.warning(f"No jobs extracted from {url}")
            return 0, 0, 0

        # Save to database
        jobs_added = 0
        jobs_updated = 0

        with self.db.session() as session:
            repo = JobRepository(session)

            for job in extraction.jobs:
                # Check if exists
                existing = None
                if job.job_id_external:
                    existing = repo.get_by_external_id(job.job_id_external)

                repo.add(job, source_url=url)

                if existing:
                    jobs_updated += 1
                else:
                    jobs_added += 1

        return jobs_found, jobs_added, jobs_updated

    async def crawl_social(
        self,
        company: str,
        keywords: list[str],
        max_results: int = 10,
    ) -> Optional[InsightSummary]:
        """Crawl social media and generate insight summary.

        Args:
            company: Company name.
            keywords: Search keywords.
            max_results: Max results per keyword.

        Returns:
            InsightSummary if successful, None otherwise.
        """
        all_notes = []

        async with XhsCrawler(headless=self.xhs_headless) as crawler:
            for keyword in keywords:
                logger.debug(f"Searching XHS: {keyword}")
                try:
                    notes = await crawler.search(keyword, max_results=max_results)
                    all_notes.extend(notes)
                    logger.debug(f"Found {len(notes)} notes for '{keyword}'")
                except Exception as e:
                    logger.warning(f"XHS search failed for '{keyword}': {e}")

        if not all_notes:
            logger.warning(f"No social posts found for {company}")
            return None

        # Deduplicate by note_id
        seen_ids = set()
        unique_notes = []
        for note in all_notes:
            if note.note_id not in seen_ids:
                seen_ids.add(note.note_id)
                unique_notes.append(note)

        logger.debug(f"Analyzing {len(unique_notes)} unique notes")

        # Generate combined keyword for insight
        combined_keyword = " / ".join(keywords)

        # Extract and summarize
        summary = await self.insight_extractor.analyze_notes(
            notes=unique_notes,
            company=company,
            position_keyword=combined_keyword,
        )

        # Save to database
        with self.db.session() as session:
            repo = InsightRepository(session)
            repo.add(summary)

        return summary

    def _get_official_url(self, company: str) -> Optional[str]:
        """Get official URL from CrawlTarget table."""
        with self.db.session() as session:
            repo = CrawlTargetRepository(session)
            targets = repo.list_by_company(company)
            for target in targets:
                if target.crawler_type == "official" and target.is_active:
                    return target.url
        return None

    def _get_social_keywords(self, company: str) -> list[str]:
        """Generate default social media search keywords."""
        return [kw.format(company=company) for kw in self.DEFAULT_SOCIAL_KEYWORDS]


async def run_intel_agent(
    company: str,
    official_url: Optional[str] = None,
    db_path: str = "data/offers.db",
    skip_official: bool = False,
    skip_social: bool = False,
) -> AgentResult:
    """Convenience function to run the intel agent.

    Args:
        company: Company name.
        official_url: Official career page URL.
        db_path: Path to database file.
        skip_official: Skip official site crawling.
        skip_social: Skip social media crawling.

    Returns:
        AgentResult with collection statistics.
    """
    db = DatabaseManager(db_path=db_path)
    db.create_tables()

    agent = IntelAgent(db)
    return await agent.run(
        company=company,
        official_url=official_url,
        skip_official=skip_official,
        skip_social=skip_social,
    )
