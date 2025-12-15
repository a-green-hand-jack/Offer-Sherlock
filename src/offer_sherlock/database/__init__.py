"""Database module for Offer-Sherlock.

Provides SQLAlchemy ORM models and CRUD operations for persisting
job postings, social insights, and crawl configurations.
"""

from offer_sherlock.database.models import (
    Base,
    CrawlTarget,
    Insight,
    Job,
    SocialPost,
)
from offer_sherlock.database.operations import (
    CrawlTargetRepository,
    InsightRepository,
    JobRepository,
)
from offer_sherlock.database.session import (
    DatabaseManager,
    get_db,
    init_db,
)

__all__ = [
    # Models
    "Base",
    "Job",
    "Insight",
    "SocialPost",
    "CrawlTarget",
    # Repositories
    "JobRepository",
    "InsightRepository",
    "CrawlTargetRepository",
    # Session management
    "DatabaseManager",
    "get_db",
    "init_db",
]
