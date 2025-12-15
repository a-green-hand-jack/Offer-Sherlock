"""LLM-powered data extractors for Offer-Sherlock.

Provides extractors for converting raw crawled content into structured data.
"""

from offer_sherlock.extractors.base import BaseExtractor
from offer_sherlock.extractors.job_extractor import JobExtractor
from offer_sherlock.extractors.insight_extractor import InsightExtractor

__all__ = [
    "BaseExtractor",
    "JobExtractor",
    "InsightExtractor",
]
