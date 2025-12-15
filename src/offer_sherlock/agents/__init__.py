"""Agent module for Offer-Sherlock.

Provides orchestration agents that coordinate the ETL pipeline.
"""

from offer_sherlock.agents.intel_agent import (
    AgentResult,
    IntelAgent,
    run_intel_agent,
)

__all__ = [
    "AgentResult",
    "IntelAgent",
    "run_intel_agent",
]
