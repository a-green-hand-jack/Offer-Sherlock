"""Intelligence collection scheduler using APScheduler.

This module provides scheduled execution of the IntelAgent for periodic
job and social intelligence collection.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import (
    EVENT_JOB_EXECUTED,
    EVENT_JOB_ERROR,
    EVENT_JOB_MISSED,
    JobExecutionEvent,
)

from offer_sherlock.agents import IntelAgent, AgentResult
from offer_sherlock.database import DatabaseManager
from offer_sherlock.utils.config import LLMProvider

logger = logging.getLogger(__name__)


@dataclass
class ScheduleConfig:
    """Configuration for scheduled intelligence collection.

    Attributes:
        db_path: Path to SQLite database file.
        llm_provider: LLM provider for extraction.
        llm_model: Model name for LLM.
        skip_social: Skip social media crawling.
        max_companies_per_run: Max companies to process per scheduled run.
        delay_between_companies: Delay between companies (anti-scraping).
        cron_hour: Hour(s) to run (cron format, e.g., "9,21" for 9AM and 9PM).
        cron_minute: Minute to run (default: 0).
        cron_day_of_week: Days to run (default: "mon-fri").
        interval_hours: Alternative: run every N hours (if set, ignores cron).
        timezone: Timezone for scheduling (default: Asia/Shanghai).
    """

    db_path: str = "data/offers.db"
    llm_provider: LLMProvider = LLMProvider.QWEN
    llm_model: str = "qwen-max"
    skip_social: bool = False
    max_companies_per_run: Optional[int] = None
    delay_between_companies: float = 2.0

    # Cron schedule (default: 9AM and 9PM on weekdays)
    cron_hour: str = "9,21"
    cron_minute: str = "0"
    cron_day_of_week: str = "mon-fri"

    # Interval schedule (overrides cron if set)
    interval_hours: Optional[float] = None

    timezone: str = "Asia/Shanghai"

    # Callbacks
    on_complete: Optional[Callable[[list[AgentResult]], None]] = None
    on_error: Optional[Callable[[Exception], None]] = None


class IntelScheduler:
    """Scheduler for periodic intelligence collection.

    Runs IntelAgent on a schedule to collect job postings and social
    intelligence from configured crawl targets.

    Example:
        >>> config = ScheduleConfig(
        ...     db_path="data/offers.db",
        ...     cron_hour="9,21",  # Run at 9AM and 9PM
        ...     skip_social=True,  # Skip XHS crawling
        ... )
        >>> scheduler = IntelScheduler(config)
        >>> scheduler.start()  # Non-blocking
        >>> # ... do other work ...
        >>> scheduler.shutdown()

        >>> # Or run blocking:
        >>> scheduler.run_blocking()
    """

    def __init__(self, config: Optional[ScheduleConfig] = None):
        """Initialize the scheduler.

        Args:
            config: Schedule configuration. Uses defaults if None.
        """
        self.config = config or ScheduleConfig()
        self._scheduler: Optional[AsyncIOScheduler] = None
        self._db: Optional[DatabaseManager] = None
        self._agent: Optional[IntelAgent] = None
        self._run_count: int = 0
        self._last_run: Optional[datetime] = None
        self._last_results: list[AgentResult] = []

    @property
    def is_running(self) -> bool:
        """Check if scheduler is currently running."""
        return self._scheduler is not None and self._scheduler.running

    @property
    def run_count(self) -> int:
        """Number of completed runs."""
        return self._run_count

    @property
    def last_run(self) -> Optional[datetime]:
        """Timestamp of last completed run."""
        return self._last_run

    @property
    def last_results(self) -> list[AgentResult]:
        """Results from the last run."""
        return self._last_results

    def _init_components(self):
        """Initialize database and agent."""
        if self._db is None:
            self._db = DatabaseManager(db_path=self.config.db_path)
            self._db.create_tables()

        if self._agent is None:
            self._agent = IntelAgent(
                db=self._db,
                llm_provider=self.config.llm_provider,
                llm_model=self.config.llm_model,
            )

    def _create_trigger(self):
        """Create the appropriate trigger based on config."""
        if self.config.interval_hours:
            return IntervalTrigger(
                hours=self.config.interval_hours,
                timezone=self.config.timezone,
            )
        else:
            return CronTrigger(
                hour=self.config.cron_hour,
                minute=self.config.cron_minute,
                day_of_week=self.config.cron_day_of_week,
                timezone=self.config.timezone,
            )

    async def _run_collection(self):
        """Execute one round of intelligence collection."""
        logger.info("Starting scheduled intelligence collection")
        start_time = datetime.now()

        try:
            self._init_components()

            results = await self._agent.run_all(
                max_companies=self.config.max_companies_per_run,
                delay_between=self.config.delay_between_companies,
            )

            self._run_count += 1
            self._last_run = datetime.now()
            self._last_results = results

            # Summary
            successful = sum(1 for r in results if r.success)
            total_jobs = sum(r.jobs_added for r in results)
            total_insights = sum(1 for r in results if r.insight_generated)
            duration = (datetime.now() - start_time).total_seconds()

            logger.info(
                f"Scheduled run #{self._run_count} complete: "
                f"{successful}/{len(results)} successful, "
                f"{total_jobs} jobs added, {total_insights} insights, "
                f"{duration:.1f}s"
            )

            # Callback
            if self.config.on_complete:
                self.config.on_complete(results)

            return results

        except Exception as e:
            logger.error(f"Scheduled collection failed: {e}")
            if self.config.on_error:
                self.config.on_error(e)
            raise

    def _on_job_event(self, event: JobExecutionEvent):
        """Handle job execution events."""
        if event.exception:
            logger.error(f"Job {event.job_id} failed: {event.exception}")
        elif hasattr(event, 'retval'):
            logger.debug(f"Job {event.job_id} completed")

    def start(self):
        """Start the scheduler in the background (non-blocking).

        The scheduler will run jobs in the current event loop.
        Call this from an async context or ensure an event loop exists.
        """
        if self._scheduler is not None:
            logger.warning("Scheduler already started")
            return

        self._scheduler = AsyncIOScheduler(timezone=self.config.timezone)

        # Add event listeners
        self._scheduler.add_listener(
            self._on_job_event,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR | EVENT_JOB_MISSED,
        )

        # Add the collection job
        trigger = self._create_trigger()
        self._scheduler.add_job(
            self._run_collection,
            trigger=trigger,
            id="intel_collection",
            name="Intelligence Collection",
            replace_existing=True,
        )

        self._scheduler.start()

        # Log schedule info
        if self.config.interval_hours:
            logger.info(f"Scheduler started: every {self.config.interval_hours} hours")
        else:
            logger.info(
                f"Scheduler started: {self.config.cron_hour}:{self.config.cron_minute} "
                f"on {self.config.cron_day_of_week} ({self.config.timezone})"
            )

    def shutdown(self, wait: bool = True):
        """Shutdown the scheduler.

        Args:
            wait: Wait for running jobs to complete.
        """
        if self._scheduler is not None:
            self._scheduler.shutdown(wait=wait)
            self._scheduler = None
            logger.info("Scheduler shutdown complete")

    async def run_once(self) -> list[AgentResult]:
        """Run intelligence collection once immediately.

        Returns:
            List of AgentResult for each company.
        """
        return await self._run_collection()

    def run_blocking(self):
        """Run the scheduler in blocking mode.

        This will block the current thread until interrupted (Ctrl+C).
        """
        import signal

        # Handle graceful shutdown
        def signal_handler(signum, frame):
            logger.info("Received shutdown signal")
            self.shutdown()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Start scheduler
        self.start()

        # Keep running
        try:
            asyncio.get_event_loop().run_forever()
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            self.shutdown()

    def get_next_run_time(self) -> Optional[datetime]:
        """Get the next scheduled run time."""
        if self._scheduler is None:
            return None

        job = self._scheduler.get_job("intel_collection")
        if job:
            return job.next_run_time
        return None

    def get_status(self) -> dict:
        """Get scheduler status information."""
        return {
            "running": self.is_running,
            "run_count": self._run_count,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "next_run": self.get_next_run_time().isoformat() if self.get_next_run_time() else None,
            "config": {
                "db_path": self.config.db_path,
                "cron_hour": self.config.cron_hour,
                "cron_minute": self.config.cron_minute,
                "cron_day_of_week": self.config.cron_day_of_week,
                "interval_hours": self.config.interval_hours,
                "timezone": self.config.timezone,
                "skip_social": self.config.skip_social,
                "max_companies_per_run": self.config.max_companies_per_run,
            },
        }


async def run_scheduler(
    db_path: str = "data/offers.db",
    cron_hour: str = "9,21",
    interval_hours: Optional[float] = None,
    skip_social: bool = False,
    run_immediately: bool = False,
) -> IntelScheduler:
    """Convenience function to create and start a scheduler.

    Args:
        db_path: Path to database file.
        cron_hour: Hour(s) to run (cron format).
        interval_hours: Run every N hours (overrides cron).
        skip_social: Skip social media crawling.
        run_immediately: Run collection immediately before starting schedule.

    Returns:
        Running IntelScheduler instance.
    """
    config = ScheduleConfig(
        db_path=db_path,
        cron_hour=cron_hour,
        interval_hours=interval_hours,
        skip_social=skip_social,
    )

    scheduler = IntelScheduler(config)

    if run_immediately:
        logger.info("Running initial collection...")
        await scheduler.run_once()

    scheduler.start()
    return scheduler
