"""SQLAlchemy ORM models for Offer-Sherlock database."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class Job(Base):
    """Official job posting from company career sites.

    Stores structured job information extracted from official recruitment pages.
    Uses job_id_external as unique identifier to prevent duplicate entries.
    """

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    job_id_external: Mapped[Optional[str]] = mapped_column(
        String(100), unique=True, nullable=True, index=True
    )
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    job_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    salary_range: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    apply_link: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    raw_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Job(id={self.id}, title='{self.title}', company='{self.company}')>"


class Insight(Base):
    """Social intelligence summary for a company/position.

    Aggregated analysis from social media posts about interview experiences,
    salary information, and overall sentiment.
    """

    __tablename__ = "insights"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    position_keyword: Mapped[str] = mapped_column(String(100), nullable=False)
    salary_estimate: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    interview_difficulty: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )
    overall_sentiment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    key_insights: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    posts_analyzed: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationship to social posts
    social_posts: Mapped[list["SocialPost"]] = relationship(
        "SocialPost", back_populates="insight", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Insight(id={self.id}, company='{self.company}', "
            f"keyword='{self.position_keyword}')>"
        )


class SocialPost(Base):
    """Individual social media post with interview/offer information.

    Stores detailed information from posts on platforms like Xiaohongshu,
    linked to an Insight summary.
    """

    __tablename__ = "social_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    insight_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("insights.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    author: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    source: Mapped[str] = mapped_column(String(50), default="xiaohongshu")
    url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    mentioned_company: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    mentioned_position: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    mentioned_salary: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sentiment: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    is_interview_experience: Mapped[bool] = mapped_column(Boolean, default=False)
    is_offer_info: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationship to insight
    insight: Mapped[Optional["Insight"]] = relationship(
        "Insight", back_populates="social_posts"
    )

    def __repr__(self) -> str:
        return f"<SocialPost(id={self.id}, title='{self.title[:30]}...')>"


class CrawlTarget(Base):
    """Configuration for crawl targets.

    Stores URLs and settings for automated crawling of job sites
    and social media searches.
    """

    __tablename__ = "crawl_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    crawler_type: Mapped[str] = mapped_column(
        String(50), default="official"
    )  # official, xhs
    css_selector: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_crawled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        status = "active" if self.is_active else "inactive"
        return f"<CrawlTarget(id={self.id}, company='{self.company}', {status})>"
