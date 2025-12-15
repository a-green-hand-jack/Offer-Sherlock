"""Tests for database ORM models."""

import pytest
from datetime import datetime

from offer_sherlock.database.models import (
    Base,
    Job,
    Insight,
    SocialPost,
    CrawlTarget,
)
from offer_sherlock.database.session import DatabaseManager


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


class TestJobModel:
    """Tests for Job model."""

    def test_create_job(self, session):
        """Test creating a job."""
        job = Job(
            company="字节跳动",
            title="后端开发工程师",
            job_id_external="JOB123",
            location="北京",
            job_type="校招",
        )
        session.add(job)
        session.flush()

        assert job.id is not None
        assert job.company == "字节跳动"
        assert job.title == "后端开发工程师"
        assert job.created_at is not None

    def test_job_repr(self, session):
        """Test Job string representation."""
        job = Job(company="Google", title="SRE")
        session.add(job)
        session.flush()

        repr_str = repr(job)
        assert "Job" in repr_str
        assert "SRE" in repr_str
        assert "Google" in repr_str

    def test_job_with_all_fields(self, session):
        """Test creating job with all fields."""
        job = Job(
            company="腾讯",
            title="前端开发",
            job_id_external="TX001",
            location="深圳",
            job_type="校招",
            requirements="熟悉 React/Vue",
            salary_range="25k-40k",
            apply_link="https://careers.tencent.com/apply/1",
            source_url="https://careers.tencent.com",
            raw_content="Full job description...",
        )
        session.add(job)
        session.flush()

        assert job.salary_range == "25k-40k"
        assert job.requirements == "熟悉 React/Vue"


class TestInsightModel:
    """Tests for Insight model."""

    def test_create_insight(self, session):
        """Test creating an insight."""
        insight = Insight(
            company="阿里巴巴",
            position_keyword="Java 后端",
            salary_estimate="30k-45k",
            interview_difficulty="medium",
            overall_sentiment="positive",
            key_insights=["面试友好", "薪资竞争力强"],
            posts_analyzed=10,
        )
        session.add(insight)
        session.flush()

        assert insight.id is not None
        assert insight.key_insights == ["面试友好", "薪资竞争力强"]

    def test_insight_repr(self, session):
        """Test Insight string representation."""
        insight = Insight(company="美团", position_keyword="算法")
        session.add(insight)
        session.flush()

        repr_str = repr(insight)
        assert "Insight" in repr_str
        assert "美团" in repr_str

    def test_insight_with_posts(self, session):
        """Test insight with related social posts."""
        insight = Insight(
            company="字节跳动",
            position_keyword="后端",
            posts_analyzed=2,
        )
        session.add(insight)
        session.flush()

        # Add related posts
        post1 = SocialPost(
            insight_id=insight.id,
            title="字节面经分享",
            content_summary="三轮技术面",
            likes=100,
        )
        post2 = SocialPost(
            insight_id=insight.id,
            title="字节offer",
            content_summary="薪资不错",
            likes=200,
        )
        session.add_all([post1, post2])
        session.flush()

        # Check relationship
        assert len(insight.social_posts) == 2


class TestSocialPostModel:
    """Tests for SocialPost model."""

    def test_create_social_post(self, session):
        """Test creating a social post."""
        post = SocialPost(
            title="腾讯面经分享",
            content_summary="两轮技术面 + HR面",
            author="求职小能手",
            likes=500,
            source="xiaohongshu",
            url="https://xiaohongshu.com/note/123",
        )
        session.add(post)
        session.flush()

        assert post.id is not None
        assert post.source == "xiaohongshu"

    def test_social_post_with_all_fields(self, session):
        """Test social post with all fields."""
        post = SocialPost(
            title="收到offer啦",
            content_summary="base 35k，股票若干",
            author="offer达人",
            likes=1000,
            source="xiaohongshu",
            url="https://xiaohongshu.com/note/456",
            mentioned_company="字节跳动",
            mentioned_position="后端开发",
            mentioned_salary="35k*15",
            sentiment="positive",
            is_interview_experience=False,
            is_offer_info=True,
        )
        session.add(post)
        session.flush()

        assert post.is_offer_info is True
        assert post.mentioned_salary == "35k*15"


class TestCrawlTargetModel:
    """Tests for CrawlTarget model."""

    def test_create_crawl_target(self, session):
        """Test creating a crawl target."""
        target = CrawlTarget(
            company="华为",
            url="https://career.huawei.com",
            crawler_type="official",
            is_active=True,
        )
        session.add(target)
        session.flush()

        assert target.id is not None
        assert target.is_active is True

    def test_crawl_target_repr(self, session):
        """Test CrawlTarget string representation."""
        target = CrawlTarget(
            company="小米",
            url="https://hr.xiaomi.com",
            is_active=False,
        )
        session.add(target)
        session.flush()

        repr_str = repr(target)
        assert "CrawlTarget" in repr_str
        assert "inactive" in repr_str

    def test_crawl_target_with_selector(self, session):
        """Test crawl target with CSS selector."""
        target = CrawlTarget(
            company="京东",
            url="https://zhaopin.jd.com",
            crawler_type="official",
            css_selector=".job-list .job-item",
        )
        session.add(target)
        session.flush()

        assert target.css_selector == ".job-list .job-item"
