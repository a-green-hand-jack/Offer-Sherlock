"""Tests for IntelScheduler."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from offer_sherlock.scheduler import IntelScheduler, ScheduleConfig
from offer_sherlock.agents import AgentResult


class TestScheduleConfig:
    """Tests for ScheduleConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ScheduleConfig()
        assert config.db_path == "data/offers.db"
        assert config.cron_hour == "9,21"
        assert config.cron_minute == "0"
        assert config.cron_day_of_week == "mon-fri"
        assert config.interval_hours is None
        assert config.skip_social is False
        assert config.timezone == "Asia/Shanghai"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ScheduleConfig(
            db_path="custom.db",
            cron_hour="8,14,20",
            interval_hours=6.0,
            skip_social=True,
            max_companies_per_run=5,
        )
        assert config.db_path == "custom.db"
        assert config.cron_hour == "8,14,20"
        assert config.interval_hours == 6.0
        assert config.skip_social is True
        assert config.max_companies_per_run == 5


class TestIntelScheduler:
    """Tests for IntelScheduler."""

    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return ScheduleConfig(
            db_path=":memory:",
            interval_hours=1.0,  # Use interval for easier testing
        )

    @pytest.fixture
    def scheduler(self, config):
        """Create scheduler instance."""
        return IntelScheduler(config)

    def test_init(self, scheduler, config):
        """Test scheduler initialization."""
        assert scheduler.config == config
        assert scheduler._scheduler is None
        assert scheduler.is_running is False
        assert scheduler.run_count == 0

    def test_is_running_false_when_not_started(self, scheduler):
        """Test is_running returns False when not started."""
        assert scheduler.is_running is False

    def test_get_status_not_running(self, scheduler):
        """Test get_status when not running."""
        status = scheduler.get_status()
        assert status["running"] is False
        assert status["run_count"] == 0
        assert status["last_run"] is None
        assert status["next_run"] is None

    def test_create_trigger_interval(self, scheduler):
        """Test trigger creation with interval."""
        trigger = scheduler._create_trigger()
        assert trigger is not None
        # IntervalTrigger has interval attribute
        assert hasattr(trigger, 'interval')

    def test_create_trigger_cron(self):
        """Test trigger creation with cron."""
        config = ScheduleConfig(
            db_path=":memory:",
            interval_hours=None,  # Use cron
            cron_hour="9",
            cron_minute="30",
        )
        scheduler = IntelScheduler(config)
        trigger = scheduler._create_trigger()
        assert trigger is not None
        # CronTrigger doesn't have interval attribute
        assert not hasattr(trigger, 'interval')

    @pytest.mark.asyncio
    async def test_run_once(self):
        """Test run_once executes collection."""
        config = ScheduleConfig(db_path=":memory:")
        scheduler = IntelScheduler(config)

        # Mock the agent
        mock_results = [
            AgentResult(company="TestCorp", success=True, jobs_added=5),
        ]

        with patch.object(
            scheduler, '_init_components'
        ), patch.object(
            scheduler, '_agent'
        ) as mock_agent:
            mock_agent.run_all = AsyncMock(return_value=mock_results)
            scheduler._agent = mock_agent

            results = await scheduler.run_once()

        assert len(results) == 1
        assert results[0].company == "TestCorp"
        assert scheduler.run_count == 1
        assert scheduler.last_run is not None

    @pytest.mark.asyncio
    async def test_run_once_calls_callback(self):
        """Test run_once calls on_complete callback."""
        callback_results = []

        def on_complete(results):
            callback_results.extend(results)

        config = ScheduleConfig(
            db_path=":memory:",
            on_complete=on_complete,
        )
        scheduler = IntelScheduler(config)

        mock_results = [
            AgentResult(company="A", success=True),
            AgentResult(company="B", success=True),
        ]

        with patch.object(
            scheduler, '_init_components'
        ), patch.object(
            scheduler, '_agent'
        ) as mock_agent:
            mock_agent.run_all = AsyncMock(return_value=mock_results)
            scheduler._agent = mock_agent

            await scheduler.run_once()

        assert len(callback_results) == 2

    @pytest.mark.asyncio
    async def test_run_once_error_callback(self):
        """Test run_once calls on_error callback on failure."""
        error_caught = []

        def on_error(error):
            error_caught.append(error)

        config = ScheduleConfig(
            db_path=":memory:",
            on_error=on_error,
        )
        scheduler = IntelScheduler(config)

        with patch.object(
            scheduler, '_init_components'
        ), patch.object(
            scheduler, '_agent'
        ) as mock_agent:
            mock_agent.run_all = AsyncMock(side_effect=Exception("Test error"))
            scheduler._agent = mock_agent

            with pytest.raises(Exception):
                await scheduler.run_once()

        assert len(error_caught) == 1
        assert "Test error" in str(error_caught[0])

    @pytest.mark.asyncio
    async def test_start_creates_scheduler(self, scheduler):
        """Test start creates and starts APScheduler."""
        scheduler.start()

        assert scheduler._scheduler is not None
        assert scheduler.is_running is True

        # Cleanup
        scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_start_idempotent(self, scheduler):
        """Test calling start twice doesn't create duplicate schedulers."""
        scheduler.start()
        first_scheduler = scheduler._scheduler

        scheduler.start()  # Should warn but not create new
        assert scheduler._scheduler is first_scheduler

        scheduler.shutdown()

    @pytest.mark.asyncio
    async def test_shutdown(self, scheduler):
        """Test shutdown stops the scheduler."""
        scheduler.start()
        assert scheduler.is_running is True

        scheduler.shutdown()
        assert scheduler.is_running is False
        assert scheduler._scheduler is None

    @pytest.mark.asyncio
    async def test_get_next_run_time_when_running(self, scheduler):
        """Test get_next_run_time returns time when running."""
        scheduler.start()

        next_run = scheduler.get_next_run_time()
        assert next_run is not None
        assert isinstance(next_run, datetime)

        scheduler.shutdown()

    def test_get_next_run_time_when_not_running(self, scheduler):
        """Test get_next_run_time returns None when not running."""
        next_run = scheduler.get_next_run_time()
        assert next_run is None

    @pytest.mark.asyncio
    async def test_get_status_when_running(self, scheduler):
        """Test get_status when scheduler is running."""
        scheduler.start()

        status = scheduler.get_status()
        assert status["running"] is True
        assert status["next_run"] is not None
        assert status["config"]["interval_hours"] == 1.0

        scheduler.shutdown()

    def test_last_results_empty_initially(self, scheduler):
        """Test last_results is empty initially."""
        assert scheduler.last_results == []

    @pytest.mark.asyncio
    async def test_last_results_updated_after_run(self):
        """Test last_results is updated after run."""
        config = ScheduleConfig(db_path=":memory:")
        scheduler = IntelScheduler(config)

        mock_results = [
            AgentResult(company="Test", success=True),
        ]

        with patch.object(
            scheduler, '_init_components'
        ), patch.object(
            scheduler, '_agent'
        ) as mock_agent:
            mock_agent.run_all = AsyncMock(return_value=mock_results)
            scheduler._agent = mock_agent

            await scheduler.run_once()

        assert len(scheduler.last_results) == 1
        assert scheduler.last_results[0].company == "Test"
