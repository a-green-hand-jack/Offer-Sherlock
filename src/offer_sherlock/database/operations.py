"""Database CRUD operations for Offer-Sherlock."""

from datetime import datetime
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from offer_sherlock.database.models import CrawlTarget, Insight, Job, SocialPost
from offer_sherlock.schemas.insight import (
    InsightSummary,
    SocialPost as SocialPostSchema,
)
from offer_sherlock.schemas.job import JobPosting


class JobRepository:
    """Repository for Job CRUD operations.

    Handles creating, reading, updating, and querying job postings.
    Supports deduplication via job_id_external.

    Example:
        >>> repo = JobRepository(session)
        >>> job = repo.add(JobPosting(title="Engineer", company="Google"))
        >>> jobs = repo.list_by_company("Google")
    """

    def __init__(self, session: Session):
        """Initialize the repository.

        Args:
            session: SQLAlchemy session to use for operations.
        """
        self.session = session

    def add(
        self,
        job: JobPosting,
        source_url: Optional[str] = None,
        raw_content: Optional[str] = None,
    ) -> Job:
        """Add a job posting to the database.

        If a job with the same job_id_external exists, updates it instead.

        Args:
            job: JobPosting schema to add.
            source_url: URL where the job was found.
            raw_content: Original raw content (optional).

        Returns:
            The created or updated Job model.
        """
        # Check for existing job by external ID
        existing = None
        if job.job_id_external:
            existing = self.get_by_external_id(job.job_id_external)

        if existing:
            # Update existing job
            existing.title = job.title
            existing.company = job.company
            existing.location = job.location
            existing.job_type = job.job_type
            existing.requirements = job.requirements
            existing.salary_range = job.salary_range
            existing.apply_link = job.apply_link
            if source_url:
                existing.source_url = source_url
            if raw_content:
                existing.raw_content = raw_content
            return existing

        # Create new job
        db_job = Job(
            company=job.company,
            title=job.title,
            job_id_external=job.job_id_external,
            location=job.location,
            job_type=job.job_type,
            requirements=job.requirements,
            salary_range=job.salary_range,
            apply_link=job.apply_link,
            source_url=source_url or job.apply_link,
            raw_content=raw_content,
        )
        self.session.add(db_job)
        self.session.flush()  # Get the ID without committing
        return db_job

    def add_many(
        self,
        jobs: list[JobPosting],
        source_url: Optional[str] = None,
    ) -> list[Job]:
        """Add multiple job postings.

        Args:
            jobs: List of JobPosting schemas to add.
            source_url: Common source URL for all jobs.

        Returns:
            List of created/updated Job models.
        """
        results = []
        for job in jobs:
            db_job = self.add(job, source_url=source_url)
            results.append(db_job)
        return results

    def get_by_id(self, job_id: int) -> Optional[Job]:
        """Get a job by its internal ID.

        Args:
            job_id: The internal database ID.

        Returns:
            Job if found, None otherwise.
        """
        return self.session.get(Job, job_id)

    def get_by_external_id(self, external_id: str) -> Optional[Job]:
        """Get a job by its external ID.

        Args:
            external_id: The external job ID from the source site.

        Returns:
            Job if found, None otherwise.
        """
        stmt = select(Job).where(Job.job_id_external == external_id)
        return self.session.scalar(stmt)

    def list_by_company(self, company: str) -> list[Job]:
        """List all jobs from a specific company.

        Args:
            company: Company name to filter by.

        Returns:
            List of Jobs from the company.
        """
        stmt = select(Job).where(Job.company == company).order_by(Job.created_at.desc())
        return list(self.session.scalars(stmt))

    def list_all(self, limit: int = 100, offset: int = 0) -> list[Job]:
        """List all jobs with pagination.

        Args:
            limit: Maximum number of jobs to return.
            offset: Number of jobs to skip.

        Returns:
            List of Jobs.
        """
        stmt = select(Job).order_by(Job.created_at.desc()).limit(limit).offset(offset)
        return list(self.session.scalars(stmt))

    def search(self, keyword: str, limit: int = 50) -> list[Job]:
        """Search jobs by keyword in title, company, or requirements.

        Args:
            keyword: Search keyword.
            limit: Maximum number of results.

        Returns:
            List of matching Jobs.
        """
        pattern = f"%{keyword}%"
        stmt = (
            select(Job)
            .where(
                or_(
                    Job.title.ilike(pattern),
                    Job.company.ilike(pattern),
                    Job.requirements.ilike(pattern),
                )
            )
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        return list(self.session.scalars(stmt))

    def count(self) -> int:
        """Get total number of jobs.

        Returns:
            Total job count.
        """
        from sqlalchemy import func

        stmt = select(func.count()).select_from(Job)
        return self.session.scalar(stmt) or 0

    def count_by_company(self, company: str) -> int:
        """Get number of jobs for a company.

        Args:
            company: Company name.

        Returns:
            Job count for the company.
        """
        from sqlalchemy import func

        stmt = select(func.count()).select_from(Job).where(Job.company == company)
        return self.session.scalar(stmt) or 0

    def delete(self, job_id: int) -> bool:
        """Delete a job by ID.

        Args:
            job_id: The job ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        job = self.get_by_id(job_id)
        if job:
            self.session.delete(job)
            return True
        return False


class InsightRepository:
    """Repository for Insight CRUD operations.

    Handles creating and querying social intelligence summaries
    along with their associated social posts.

    Example:
        >>> repo = InsightRepository(session)
        >>> insight = repo.add(insight_summary)
        >>> latest = repo.get_latest_by_company("字节跳动")
    """

    def __init__(self, session: Session):
        """Initialize the repository.

        Args:
            session: SQLAlchemy session to use for operations.
        """
        self.session = session

    def add(self, summary: InsightSummary) -> Insight:
        """Add an insight summary with its social posts.

        Args:
            summary: InsightSummary schema to add.

        Returns:
            The created Insight model.
        """
        # Create insight
        db_insight = Insight(
            company=summary.company,
            position_keyword=summary.position_keyword,
            salary_estimate=summary.salary_estimate,
            interview_difficulty=(
                summary.interview_difficulty.value
                if summary.interview_difficulty
                else None
            ),
            overall_sentiment=(
                summary.overall_sentiment.value if summary.overall_sentiment else None
            ),
            key_insights=summary.key_insights,
            recommendation=summary.recommendation,
            posts_analyzed=summary.posts_analyzed,
        )
        self.session.add(db_insight)
        self.session.flush()  # Get the insight ID

        # Add associated social posts
        for post_schema in summary.source_posts:
            db_post = self._create_social_post(post_schema, db_insight.id)
            self.session.add(db_post)

        return db_insight

    def _create_social_post(
        self, post: SocialPostSchema, insight_id: int
    ) -> SocialPost:
        """Create a SocialPost model from schema.

        Args:
            post: SocialPost schema.
            insight_id: ID of the parent Insight.

        Returns:
            SocialPost model instance.
        """
        return SocialPost(
            insight_id=insight_id,
            title=post.title,
            content_summary=post.content_summary,
            author=post.author,
            likes=post.likes,
            source=post.source,
            url=post.url,
            mentioned_company=post.mentioned_company,
            mentioned_position=post.mentioned_position,
            mentioned_salary=post.mentioned_salary,
            sentiment=post.sentiment.value if post.sentiment else None,
            is_interview_experience=post.is_interview_experience,
            is_offer_info=post.is_offer_info,
        )

    def get_by_id(self, insight_id: int) -> Optional[Insight]:
        """Get an insight by ID.

        Args:
            insight_id: The insight ID.

        Returns:
            Insight if found, None otherwise.
        """
        return self.session.get(Insight, insight_id)

    def get_latest_by_company(
        self, company: str, position_keyword: Optional[str] = None
    ) -> Optional[Insight]:
        """Get the most recent insight for a company.

        Args:
            company: Company name.
            position_keyword: Optional position keyword to filter.

        Returns:
            Most recent Insight if found, None otherwise.
        """
        stmt = select(Insight).where(Insight.company == company)
        if position_keyword:
            stmt = stmt.where(Insight.position_keyword == position_keyword)
        stmt = stmt.order_by(Insight.created_at.desc()).limit(1)
        return self.session.scalar(stmt)

    def list_by_company(self, company: str) -> list[Insight]:
        """List all insights for a company.

        Args:
            company: Company name.

        Returns:
            List of Insights for the company.
        """
        stmt = (
            select(Insight)
            .where(Insight.company == company)
            .order_by(Insight.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def list_all(self, limit: int = 100, offset: int = 0) -> list[Insight]:
        """List all insights with pagination.

        Args:
            limit: Maximum number of insights.
            offset: Number to skip.

        Returns:
            List of Insights.
        """
        stmt = (
            select(Insight).order_by(Insight.created_at.desc()).limit(limit).offset(offset)
        )
        return list(self.session.scalars(stmt))

    def count(self) -> int:
        """Get total number of insights.

        Returns:
            Total insight count.
        """
        from sqlalchemy import func

        stmt = select(func.count()).select_from(Insight)
        return self.session.scalar(stmt) or 0

    def delete(self, insight_id: int) -> bool:
        """Delete an insight and its posts.

        Args:
            insight_id: The insight ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        insight = self.get_by_id(insight_id)
        if insight:
            self.session.delete(insight)  # Cascades to social_posts
            return True
        return False


class CrawlTargetRepository:
    """Repository for CrawlTarget CRUD operations.

    Manages crawl target configurations for automated job scraping.

    Example:
        >>> repo = CrawlTargetRepository(session)
        >>> repo.add("字节跳动", "https://jobs.bytedance.com", "official")
        >>> targets = repo.list_active()
    """

    def __init__(self, session: Session):
        """Initialize the repository.

        Args:
            session: SQLAlchemy session to use.
        """
        self.session = session

    def add(
        self,
        company: str,
        url: str,
        crawler_type: str = "official",
        css_selector: Optional[str] = None,
        is_active: bool = True,
    ) -> CrawlTarget:
        """Add a new crawl target.

        Args:
            company: Company name.
            url: URL to crawl.
            crawler_type: Type of crawler (official/xhs).
            css_selector: Optional CSS selector for content.
            is_active: Whether the target is active.

        Returns:
            The created CrawlTarget.
        """
        target = CrawlTarget(
            company=company,
            url=url,
            crawler_type=crawler_type,
            css_selector=css_selector,
            is_active=is_active,
        )
        self.session.add(target)
        self.session.flush()
        return target

    def get_by_id(self, target_id: int) -> Optional[CrawlTarget]:
        """Get a crawl target by ID.

        Args:
            target_id: The target ID.

        Returns:
            CrawlTarget if found, None otherwise.
        """
        return self.session.get(CrawlTarget, target_id)

    def list_active(self) -> list[CrawlTarget]:
        """List all active crawl targets.

        Returns:
            List of active CrawlTargets.
        """
        stmt = select(CrawlTarget).where(CrawlTarget.is_active == True)
        return list(self.session.scalars(stmt))

    def list_by_company(self, company: str) -> list[CrawlTarget]:
        """List crawl targets for a company.

        Args:
            company: Company name.

        Returns:
            List of CrawlTargets.
        """
        stmt = select(CrawlTarget).where(CrawlTarget.company == company)
        return list(self.session.scalars(stmt))

    def list_all(self) -> list[CrawlTarget]:
        """List all crawl targets.

        Returns:
            List of all CrawlTargets.
        """
        stmt = select(CrawlTarget).order_by(CrawlTarget.company)
        return list(self.session.scalars(stmt))

    def update_last_crawled(self, target_id: int) -> bool:
        """Update the last crawled timestamp.

        Args:
            target_id: The target ID.

        Returns:
            True if updated, False if not found.
        """
        target = self.get_by_id(target_id)
        if target:
            target.last_crawled_at = datetime.now()
            return True
        return False

    def set_active(self, target_id: int, is_active: bool) -> bool:
        """Set the active status of a target.

        Args:
            target_id: The target ID.
            is_active: New active status.

        Returns:
            True if updated, False if not found.
        """
        target = self.get_by_id(target_id)
        if target:
            target.is_active = is_active
            return True
        return False

    def delete(self, target_id: int) -> bool:
        """Delete a crawl target.

        Args:
            target_id: The target ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        target = self.get_by_id(target_id)
        if target:
            self.session.delete(target)
            return True
        return False
