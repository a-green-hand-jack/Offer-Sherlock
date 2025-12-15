"""Crawlers module for Offer-Sherlock.

Provides web scraping capabilities for official job sites and social media.
"""

from offer_sherlock.crawlers.base import BaseCrawler, CrawlResult
from offer_sherlock.crawlers.official_crawler import CrawlTarget, OfficialCrawler
from offer_sherlock.crawlers.social_crawler import XhsCrawler, XhsNote

__all__ = [
    "BaseCrawler",
    "CrawlResult",
    "CrawlTarget",
    "OfficialCrawler",
    "XhsCrawler",
    "XhsNote",
]
