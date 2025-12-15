"""Tests for database CRUD operations."""

import pytest

from offer_sherlock.database.models import Job, Insight
from offer_sherlock.database.operations import (
    JobRepository,
    InsightRepository,
    CrawlTargetRepository,
)
from offer_sherlock.database.session import DatabaseManager
from offer_sherlock.schemas.job import JobPosting
from offer_sherlock.schemas.insight import (
    InsightSummary,
    SocialPost as SocialPostSchema,
    Sentiment,
    InterviewDifficulty,
)


@pytest.fixture
def db():
    """Create an in-memory database for testing."""
    manager = DatabaseManager(db_path=":memory:")
    manager.create_tables()
    return manager


@pytest.fixture
def session(db):
    """Get a database session."""
    with db.session() as sess:
        yield sess


class TestJobRepository:
    """Tests for JobRepository."""

    def test_add_job(self, session):
        """Test adding a job."""
        repo = JobRepository(session)
        job_schema = JobPosting(
            title="后端开发工程师",
            company="字节跳动",
            job_id_external="JOB001",
            location="北京",
        )

        job = repo.add(job_schema, source_url="https://jobs.bytedance.com")

        assert job.id is not None
        assert job.title == "后端开发工程师"
        assert job.source_url == "https://jobs.bytedance.com"

    def test_add_duplicate_updates(self, session):
        """Test that adding duplicate external ID updates existing job."""
        repo = JobRepository(session)

        # Add initial job
        job1 = JobPosting(
            title="工程师",
            company="Google",
            job_id_external="G001",
            location="Mountain View",
        )
        repo.add(job1)
        session.flush()

        # Add job with same external ID
        job2 = JobPosting(
            title="Senior 工程师",  # Updated title
            company="Google",
            job_id_external="G001",
            location="Sunnyvale",  # Updated location
        )
        updated = repo.add(job2)

        assert updated.title == "Senior 工程师"
        assert updated.location == "Sunnyvale"
        assert repo.count() == 1  # Still only one job

    def test_add_many(self, session):
        """Test adding multiple jobs."""
        repo = JobRepository(session)
        jobs = [
            JobPosting(title="前端", company="腾讯", job_id_external="TX001"),
            JobPosting(title="后端", company="腾讯", job_id_external="TX002"),
            JobPosting(title="算法", company="腾讯", job_id_external="TX003"),
        ]

        result = repo.add_many(jobs, source_url="https://careers.tencent.com")

        assert len(result) == 3
        assert repo.count() == 3

    def test_get_by_external_id(self, session):
        """Test getting job by external ID."""
        repo = JobRepository(session)
        repo.add(
            JobPosting(title="测试", company="阿里", job_id_external="ALI001")
        )
        session.flush()

        job = repo.get_by_external_id("ALI001")
        assert job is not None
        assert job.company == "阿里"

        not_found = repo.get_by_external_id("NOTEXIST")
        assert not_found is None

    def test_list_by_company(self, session):
        """Test listing jobs by company."""
        repo = JobRepository(session)
        repo.add_many([
            JobPosting(title="岗位1", company="华为", job_id_external="HW001"),
            JobPosting(title="岗位2", company="华为", job_id_external="HW002"),
            JobPosting(title="岗位3", company="小米", job_id_external="MI001"),
        ])
        session.flush()

        huawei_jobs = repo.list_by_company("华为")
        assert len(huawei_jobs) == 2

        xiaomi_jobs = repo.list_by_company("小米")
        assert len(xiaomi_jobs) == 1

    def test_search(self, session):
        """Test searching jobs by keyword."""
        repo = JobRepository(session)
        repo.add_many([
            JobPosting(
                title="Python 后端开发",
                company="字节",
                job_id_external="B001",
                requirements="熟悉 Python 和 Django",
            ),
            JobPosting(
                title="Java 后端开发",
                company="阿里",
                job_id_external="A001",
                requirements="熟悉 Java 和 Spring",
            ),
            JobPosting(
                title="前端开发",
                company="腾讯",
                job_id_external="T001",
            ),
        ])
        session.flush()

        # Search by title
        results = repo.search("后端")
        assert len(results) == 2

        # Search by requirements
        results = repo.search("Python")
        assert len(results) == 1
        assert results[0].company == "字节"

    def test_delete(self, session):
        """Test deleting a job."""
        repo = JobRepository(session)
        job = repo.add(
            JobPosting(title="临时岗位", company="测试公司", job_id_external="TMP")
        )
        session.flush()
        job_id = job.id

        assert repo.delete(job_id) is True
        session.flush()
        session.expire_all()  # Clear cache to see actual DB state
        assert repo.get_by_id(job_id) is None
        assert repo.delete(9999) is False  # Non-existent


class TestInsightRepository:
    """Tests for InsightRepository."""

    def test_add_insight(self, session):
        """Test adding an insight."""
        repo = InsightRepository(session)
        summary = InsightSummary(
            company="美团",
            position_keyword="后端",
            salary_estimate="25k-35k",
            interview_difficulty=InterviewDifficulty.MEDIUM,
            overall_sentiment=Sentiment.POSITIVE,
            key_insights=["面试友好", "技术氛围好"],
            recommendation="推荐投递",
            posts_analyzed=5,
        )

        insight = repo.add(summary)

        assert insight.id is not None
        assert insight.company == "美团"
        assert insight.interview_difficulty == "medium"
        assert insight.overall_sentiment == "positive"

    def test_add_insight_with_posts(self, session):
        """Test adding insight with social posts."""
        repo = InsightRepository(session)
        posts = [
            SocialPostSchema(
                title="美团面经",
                content_summary="三轮技术面",
                author="求职者A",
                likes=100,
                sentiment=Sentiment.POSITIVE,
            ),
            SocialPostSchema(
                title="美团offer",
                content_summary="薪资还行",
                author="求职者B",
                likes=200,
                mentioned_salary="28k*15",
                sentiment=Sentiment.POSITIVE,
                is_offer_info=True,
            ),
        ]
        summary = InsightSummary(
            company="美团",
            position_keyword="算法",
            source_posts=posts,
            posts_analyzed=2,
        )

        insight = repo.add(summary)
        session.flush()

        # Check posts were created
        assert len(insight.social_posts) == 2
        assert insight.social_posts[0].title == "美团面经"
        assert insight.social_posts[1].is_offer_info is True

    def test_get_latest_by_company(self, session):
        """Test getting latest insight for a company."""
        repo = InsightRepository(session)

        # Add multiple insights for 京东
        repo.add(InsightSummary(company="京东", position_keyword="后端", posts_analyzed=1))
        session.flush()
        repo.add(InsightSummary(company="拼多多", position_keyword="后端", posts_analyzed=3))
        session.flush()

        # Get latest for 京东
        latest = repo.get_latest_by_company("京东")
        assert latest is not None
        assert latest.company == "京东"

        # Get latest with keyword filter
        latest = repo.get_latest_by_company("京东", position_keyword="后端")
        assert latest is not None
        assert latest.position_keyword == "后端"

        # Non-existent
        not_found = repo.get_latest_by_company("不存在的公司")
        assert not_found is None

    def test_list_by_company(self, session):
        """Test listing insights by company."""
        repo = InsightRepository(session)
        repo.add(InsightSummary(company="B站", position_keyword="后端", posts_analyzed=1))
        repo.add(InsightSummary(company="B站", position_keyword="前端", posts_analyzed=1))
        repo.add(InsightSummary(company="网易", position_keyword="游戏", posts_analyzed=1))
        session.flush()

        bilibili = repo.list_by_company("B站")
        assert len(bilibili) == 2

    def test_delete_cascades_to_posts(self, session):
        """Test that deleting insight also deletes posts."""
        repo = InsightRepository(session)
        posts = [
            SocialPostSchema(title="帖子1", content_summary="内容1", likes=10),
            SocialPostSchema(title="帖子2", content_summary="内容2", likes=20),
        ]
        summary = InsightSummary(
            company="测试",
            position_keyword="测试",
            source_posts=posts,
            posts_analyzed=2,
        )
        insight = repo.add(summary)
        session.flush()
        insight_id = insight.id

        # Verify posts exist
        from sqlalchemy import select
        from offer_sherlock.database.models import SocialPost
        stmt = select(SocialPost).where(SocialPost.insight_id == insight_id)
        posts_before = list(session.scalars(stmt))
        assert len(posts_before) == 2

        # Delete insight
        assert repo.delete(insight_id) is True
        session.flush()
        session.expire_all()  # Clear cache

        # Verify insight is deleted
        assert repo.get_by_id(insight_id) is None

        # Verify posts are also deleted (cascade)
        stmt = select(SocialPost).where(SocialPost.insight_id == insight_id)
        remaining = list(session.scalars(stmt))
        assert len(remaining) == 0


class TestCrawlTargetRepository:
    """Tests for CrawlTargetRepository."""

    def test_add_target(self, session):
        """Test adding a crawl target."""
        repo = CrawlTargetRepository(session)

        target = repo.add(
            company="滴滴",
            url="https://talent.didiglobal.com",
            crawler_type="official",
        )

        assert target.id is not None
        assert target.is_active is True

    def test_list_active(self, session):
        """Test listing active targets."""
        repo = CrawlTargetRepository(session)
        repo.add("公司A", "https://a.com", is_active=True)
        repo.add("公司B", "https://b.com", is_active=False)
        repo.add("公司C", "https://c.com", is_active=True)
        session.flush()

        active = repo.list_active()
        assert len(active) == 2

    def test_update_last_crawled(self, session):
        """Test updating last crawled timestamp."""
        repo = CrawlTargetRepository(session)
        target = repo.add("测试", "https://test.com")
        session.flush()

        assert target.last_crawled_at is None

        repo.update_last_crawled(target.id)
        session.flush()

        assert target.last_crawled_at is not None

    def test_set_active(self, session):
        """Test toggling active status."""
        repo = CrawlTargetRepository(session)
        target = repo.add("测试", "https://test.com", is_active=True)
        session.flush()

        repo.set_active(target.id, False)
        assert target.is_active is False

        repo.set_active(target.id, True)
        assert target.is_active is True
