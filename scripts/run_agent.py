#!/usr/bin/env python3
"""CLI script to run the intelligence collection agent.

Usage:
    # Single company with official URL
    python scripts/run_agent.py --company "字节跳动" --url "https://jobs.bytedance.com"

    # Single company, social only
    python scripts/run_agent.py --company "腾讯" --skip-official

    # Batch mode (all active targets)
    python scripts/run_agent.py --all

    # Add a new crawl target
    python scripts/run_agent.py --add-target --company "华为" --url "https://career.huawei.com"
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from offer_sherlock.agents import IntelAgent, AgentResult
from offer_sherlock.database import (
    DatabaseManager,
    CrawlTargetRepository,
    JobRepository,
    InsightRepository,
)


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def print_result(result: AgentResult):
    """Print a single result in a nice format."""
    print(f"\n{result}")
    if result.errors:
        for error in result.errors:
            print(f"  ⚠️  {error}")


def print_summary(results: list[AgentResult]):
    """Print summary of batch results."""
    print("\n" + "=" * 60)
    print("📊 运行结果汇总")
    print("=" * 60)

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    print(f"\n总公司数: {len(results)}")
    print(f"成功: {len(successful)}")
    print(f"失败: {len(failed)}")

    total_jobs = sum(r.jobs_added for r in results)
    total_insights = sum(1 for r in results if r.insight_generated)
    total_time = sum(r.duration_seconds for r in results)

    print(f"\n新增岗位: {total_jobs}")
    print(f"生成情报: {total_insights}")
    print(f"总耗时: {total_time:.1f}s")

    if failed:
        print("\n❌ 失败的公司:")
        for r in failed:
            print(f"  - {r.company}: {', '.join(r.errors)}")


async def run_single(
    db: DatabaseManager,
    company: str,
    url: str = None,
    skip_official: bool = False,
    skip_social: bool = False,
    headless: bool = True,
):
    """Run agent for a single company."""
    print(f"\n🚀 开始收集 {company} 情报...")

    agent = IntelAgent(db, xhs_headless=headless)
    result = await agent.run(
        company=company,
        official_url=url,
        skip_official=skip_official,
        skip_social=skip_social,
    )

    print_result(result)
    return result


async def run_batch(
    db: DatabaseManager,
    max_companies: int = None,
    headless: bool = True,
):
    """Run agent for all active targets."""
    with db.session() as session:
        target_repo = CrawlTargetRepository(session)
        targets = target_repo.list_active()

    if not targets:
        print("❌ 没有活跃的抓取目标")
        print("   使用 --add-target 添加目标")
        return []

    count = len(targets) if not max_companies else min(len(targets), max_companies)
    print(f"\n🚀 开始批量收集 {count} 家公司情报...")

    agent = IntelAgent(db, xhs_headless=headless)
    results = await agent.run_all(max_companies=max_companies)

    for result in results:
        print_result(result)

    print_summary(results)
    return results


def add_target(db: DatabaseManager, company: str, url: str, crawler_type: str = "official"):
    """Add a new crawl target."""
    with db.session() as session:
        repo = CrawlTargetRepository(session)

        # Check if already exists
        existing = repo.list_by_company(company)
        for t in existing:
            if t.url == url:
                print(f"⚠️  目标已存在: {company} - {url}")
                return

        repo.add(company=company, url=url, crawler_type=crawler_type)
        print(f"✅ 已添加目标: {company} - {url}")


def list_targets(db: DatabaseManager):
    """List all crawl targets."""
    with db.session() as session:
        repo = CrawlTargetRepository(session)
        targets = repo.list_all()

    print("\n📋 抓取目标列表")
    print("=" * 60)

    if not targets:
        print("(空)")
        return

    for t in targets:
        status = "✅" if t.is_active else "⏸️"
        last = t.last_crawled_at.strftime("%Y-%m-%d %H:%M") if t.last_crawled_at else "从未"
        print(f"{status} {t.company}")
        print(f"   URL: {t.url}")
        print(f"   类型: {t.crawler_type} | 上次抓取: {last}")
        print()


def show_stats(db: DatabaseManager):
    """Show database statistics."""
    with db.session() as session:
        job_repo = JobRepository(session)
        insight_repo = InsightRepository(session)
        target_repo = CrawlTargetRepository(session)

        print("\n📊 数据库统计")
        print("=" * 60)
        print(f"总岗位数: {job_repo.count()}")
        print(f"总情报数: {insight_repo.count()}")
        print(f"抓取目标: {len(target_repo.list_all())} (活跃: {len(target_repo.list_active())})")

        # Top companies by job count
        from sqlalchemy import select, func
        from offer_sherlock.database.models import Job

        stmt = (
            select(Job.company, func.count(Job.id).label("count"))
            .group_by(Job.company)
            .order_by(func.count(Job.id).desc())
            .limit(5)
        )
        top_companies = list(session.execute(stmt))

        if top_companies:
            print("\n岗位数 Top 5:")
            for company, count in top_companies:
                print(f"  - {company}: {count}")


def main():
    parser = argparse.ArgumentParser(
        description="Offer-Sherlock 情报收集 Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 单公司模式
  python scripts/run_agent.py --company "字节跳动" --url "https://jobs.bytedance.com"

  # 只抓取社交情报
  python scripts/run_agent.py --company "腾讯" --skip-official

  # 批量模式
  python scripts/run_agent.py --all

  # 添加抓取目标
  python scripts/run_agent.py --add-target --company "华为" --url "https://career.huawei.com"

  # 查看状态
  python scripts/run_agent.py --list-targets
  python scripts/run_agent.py --stats
        """,
    )

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--company", "-c",
        help="单公司模式: 指定公司名称",
    )
    mode_group.add_argument(
        "--all", "-a",
        action="store_true",
        help="批量模式: 运行所有活跃目标",
    )
    mode_group.add_argument(
        "--add-target",
        action="store_true",
        help="添加新的抓取目标",
    )
    mode_group.add_argument(
        "--list-targets",
        action="store_true",
        help="列出所有抓取目标",
    )
    mode_group.add_argument(
        "--stats",
        action="store_true",
        help="显示数据库统计",
    )

    # Options
    parser.add_argument(
        "--url", "-u",
        help="官网招聘 URL",
    )
    parser.add_argument(
        "--skip-official",
        action="store_true",
        help="跳过官网抓取",
    )
    parser.add_argument(
        "--skip-social",
        action="store_true",
        help="跳过社交情报",
    )
    parser.add_argument(
        "--max-companies", "-m",
        type=int,
        help="批量模式: 最大公司数",
    )
    parser.add_argument(
        "--db",
        default="data/offers.db",
        help="数据库路径 (默认: data/offers.db)",
    )
    parser.add_argument(
        "--no-headless",
        action="store_true",
        help="显示浏览器窗口 (用于调试)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="显示详细日志",
    )

    args = parser.parse_args()

    # Setup
    setup_logging(args.verbose)
    db = DatabaseManager(db_path=args.db)
    db.create_tables()

    # Execute
    if args.list_targets:
        list_targets(db)
    elif args.stats:
        show_stats(db)
    elif args.add_target:
        if not args.company or not args.url:
            print("❌ 添加目标需要 --company 和 --url")
            sys.exit(1)
        add_target(db, args.company, args.url)
    elif args.all:
        asyncio.run(run_batch(
            db,
            max_companies=args.max_companies,
            headless=not args.no_headless,
        ))
    elif args.company:
        asyncio.run(run_single(
            db,
            company=args.company,
            url=args.url,
            skip_official=args.skip_official,
            skip_social=args.skip_social,
            headless=not args.no_headless,
        ))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
