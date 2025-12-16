#!/usr/bin/env python3
"""Run the intelligence collection scheduler.

This script starts the IntelScheduler to periodically collect job postings
and social intelligence from configured crawl targets.

Usage:
    # Default: Run at 9AM and 9PM on weekdays
    python scripts/run_scheduler.py

    # Run every 6 hours
    python scripts/run_scheduler.py --interval 6

    # Custom cron schedule (8AM, 2PM, 8PM daily)
    python scripts/run_scheduler.py --cron-hour "8,14,20" --cron-day "*"

    # Run immediately, then continue on schedule
    python scripts/run_scheduler.py --run-now

    # Skip social media crawling
    python scripts/run_scheduler.py --skip-social

    # Show status and exit
    python scripts/run_scheduler.py --status
"""

import argparse
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

from offer_sherlock.scheduler import IntelScheduler, ScheduleConfig
from offer_sherlock.database import DatabaseManager, CrawlTargetRepository

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def show_status(db_path: str):
    """Show current targets and database status."""
    db = DatabaseManager(db_path=db_path)

    with db.session() as session:
        repo = CrawlTargetRepository(session)
        targets = repo.list_active()

        print("\n📋 活跃抓取目标")
        print("=" * 60)

        if not targets:
            print("(无活跃目标 - 运行 python scripts/init_targets.py 初始化)")
            return

        for t in targets:
            last_crawled = t.last_crawled_at.strftime("%Y-%m-%d %H:%M") if t.last_crawled_at else "从未"
            print(f"  {t.company:<12} | 上次抓取: {last_crawled}")

        print(f"\n总计: {len(targets)} 个活跃目标")


def on_collection_complete(results):
    """Callback when collection completes."""
    successful = sum(1 for r in results if r.success)
    jobs_added = sum(r.jobs_added for r in results)
    insights = sum(1 for r in results if r.insight_generated)

    print(f"\n{'=' * 60}")
    print(f"✅ 采集完成: {successful}/{len(results)} 成功")
    print(f"   新增岗位: {jobs_added}")
    print(f"   生成情报: {insights}")
    print(f"{'=' * 60}\n")


def on_collection_error(error):
    """Callback when collection fails."""
    print(f"\n❌ 采集失败: {error}\n")


async def main():
    parser = argparse.ArgumentParser(
        description="运行情报收集调度器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Schedule options
    schedule_group = parser.add_argument_group("调度选项")
    schedule_group.add_argument(
        "--interval",
        type=float,
        help="每 N 小时运行一次 (覆盖 cron 设置)",
    )
    schedule_group.add_argument(
        "--cron-hour",
        default="9,21",
        help="运行时间 (cron 格式, 默认: 9,21 即 9AM 和 9PM)",
    )
    schedule_group.add_argument(
        "--cron-minute",
        default="0",
        help="运行分钟 (默认: 0)",
    )
    schedule_group.add_argument(
        "--cron-day",
        default="mon-fri",
        help="运行日期 (cron 格式, 默认: mon-fri, 用 * 表示每天)",
    )
    schedule_group.add_argument(
        "--timezone",
        default="Asia/Shanghai",
        help="时区 (默认: Asia/Shanghai)",
    )

    # Collection options
    collect_group = parser.add_argument_group("采集选项")
    collect_group.add_argument(
        "--skip-social",
        action="store_true",
        help="跳过社交媒体抓取 (小红书)",
    )
    collect_group.add_argument(
        "--max-companies",
        type=int,
        help="每次运行最多处理公司数",
    )
    collect_group.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="公司间延迟秒数 (默认: 2.0)",
    )

    # Database options
    db_group = parser.add_argument_group("数据库选项")
    db_group.add_argument(
        "--db",
        default="data/offers.db",
        help="数据库路径 (默认: data/offers.db)",
    )

    # Actions
    action_group = parser.add_argument_group("操作")
    action_group.add_argument(
        "--run-now",
        action="store_true",
        help="立即运行一次，然后继续按计划执行",
    )
    action_group.add_argument(
        "--once",
        action="store_true",
        help="只运行一次，不启动调度器",
    )
    action_group.add_argument(
        "--status",
        action="store_true",
        help="显示当前状态并退出",
    )

    args = parser.parse_args()

    # Ensure data directory exists
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)

    # Show status and exit
    if args.status:
        show_status(args.db)
        return

    # Create configuration
    config = ScheduleConfig(
        db_path=args.db,
        skip_social=args.skip_social,
        max_companies_per_run=args.max_companies,
        delay_between_companies=args.delay,
        cron_hour=args.cron_hour,
        cron_minute=args.cron_minute,
        cron_day_of_week=args.cron_day if args.cron_day != "*" else "mon-sun",
        interval_hours=args.interval,
        timezone=args.timezone,
        on_complete=on_collection_complete,
        on_error=on_collection_error,
    )

    scheduler = IntelScheduler(config)

    # Run once mode
    if args.once:
        print("\n🚀 运行一次情报采集...")
        print("=" * 60)
        results = await scheduler.run_once()

        print("\n📊 采集结果")
        print("-" * 60)
        for r in results:
            print(str(r))

        successful = sum(1 for r in results if r.success)
        print(f"\n✅ 完成: {successful}/{len(results)} 成功")
        return

    # Start scheduler
    print("\n🕐 启动情报采集调度器")
    print("=" * 60)
    print(f"数据库: {args.db}")

    if args.interval:
        print(f"调度: 每 {args.interval} 小时")
    else:
        day_str = "每天" if args.cron_day in ("*", "mon-sun") else args.cron_day
        print(f"调度: {args.cron_hour}:{args.cron_minute} ({day_str})")

    print(f"时区: {args.timezone}")
    print(f"跳过社交: {'是' if args.skip_social else '否'}")

    if args.max_companies:
        print(f"每次最多: {args.max_companies} 家公司")

    # Run immediately if requested
    if args.run_now:
        print("\n⚡ 立即执行首次采集...")
        await scheduler.run_once()

    # Start the scheduler
    scheduler.start()

    next_run = scheduler.get_next_run_time()
    if next_run:
        print(f"\n⏰ 下次运行: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

    print("\n按 Ctrl+C 停止调度器\n")

    # Keep running
    try:
        while True:
            await asyncio.sleep(60)

            # Periodic status update
            status = scheduler.get_status()
            if status["run_count"] > 0:
                next_run = scheduler.get_next_run_time()
                if next_run:
                    remaining = (next_run - datetime.now(next_run.tzinfo)).total_seconds()
                    if remaining > 0:
                        hours, remainder = divmod(int(remaining), 3600)
                        minutes, _ = divmod(remainder, 60)
                        # Only log occasionally
                        if minutes == 0:
                            logger.debug(f"下次运行: {hours}h {minutes}m")

    except KeyboardInterrupt:
        print("\n\n🛑 正在停止调度器...")
        scheduler.shutdown()
        print("✅ 调度器已停止")


if __name__ == "__main__":
    asyncio.run(main())
