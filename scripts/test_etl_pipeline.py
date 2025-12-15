#!/usr/bin/env python3
"""Integration test for the complete ETL pipeline.

Tests the full flow:
1. Extract: Crawl official sites and XHS
2. Transform: Use LLM to extract structured data
3. Load: Persist to SQLite database
"""

import asyncio
from pathlib import Path

from offer_sherlock.crawlers import OfficialCrawler, XhsCrawler
from offer_sherlock.extractors import JobExtractor, InsightExtractor
from offer_sherlock.database import (
    DatabaseManager,
    JobRepository,
    InsightRepository,
    CrawlTargetRepository,
)
from offer_sherlock.llm.client import LLMClient
from offer_sherlock.utils.config import LLMProvider


async def test_job_etl():
    """Test ETL for official job postings."""
    print("=" * 60)
    print("🧪 测试 Job ETL Pipeline")
    print("=" * 60)

    # Setup database
    db = DatabaseManager(db_path="data/test_etl.db")
    db.create_tables()

    # Use existing crawl results
    data_dir = Path(__file__).parent.parent / "data" / "crawl_results"
    google_file = data_dir / "Google.md"

    if not google_file.exists():
        print("❌ 未找到 Google.md，跳过测试")
        return

    print(f"\n📖 读取: {google_file.name}")
    content = google_file.read_text()[:12000]

    # Extract
    print("🤖 使用 Qwen-plus 提取岗位信息...")
    llm = LLMClient(provider=LLMProvider.QWEN, model="qwen-plus")
    extractor = JobExtractor(llm_client=llm)

    result = await extractor.extract(
        content=content,
        company="Google",
        source_url="https://careers.google.com",
    )

    print(f"✅ 提取到 {result.count} 个岗位")

    # Load to database
    print("\n💾 保存到数据库...")
    with db.session() as session:
        repo = JobRepository(session)

        # Add crawl target
        target_repo = CrawlTargetRepository(session)
        target_repo.add(
            company="Google",
            url="https://careers.google.com",
            crawler_type="official",
        )

        # Add jobs
        jobs = repo.add_many(result.jobs, source_url=result.source_url)
        print(f"✅ 保存了 {len(jobs)} 个岗位")

        # Query back
        google_jobs = repo.list_by_company("Google")
        print(f"\n📊 数据库中 Google 岗位数: {len(google_jobs)}")

        for job in google_jobs[:3]:
            print(f"  - {job.title} [{job.location or '未知'}]")


async def test_insight_etl():
    """Test ETL for social insights."""
    print("\n" + "=" * 60)
    print("🧪 测试 Insight ETL Pipeline")
    print("=" * 60)

    # Setup database
    db = DatabaseManager(db_path="data/test_etl.db")
    db.create_tables()

    # Search XHS
    print("\n🔍 搜索小红书: 腾讯 offer")

    async with XhsCrawler(headless=True) as crawler:
        notes = await crawler.search("腾讯 offer", max_results=5)

        if not notes:
            print("❌ 未找到笔记，跳过测试")
            return

        print(f"📖 找到 {len(notes)} 条笔记")

        # Extract
        print("\n🤖 使用 Qwen-plus 分析笔记...")
        llm = LLMClient(provider=LLMProvider.QWEN, model="qwen-plus")
        extractor = InsightExtractor(llm_client=llm)

        summary = await extractor.analyze_notes(
            notes=notes,
            company="腾讯",
            position_keyword="offer",
        )

        print(f"✅ 生成情报汇总: {summary.overall_sentiment.value}")

        # Load to database
        print("\n💾 保存到数据库...")
        with db.session() as session:
            repo = InsightRepository(session)
            insight = repo.add(summary)
            print(f"✅ 保存情报 ID: {insight.id}")
            print(f"   关联帖子数: {len(insight.social_posts)}")

            # Query back
            latest = repo.get_latest_by_company("腾讯")
            if latest:
                print(f"\n📊 最新情报:")
                print(f"   公司: {latest.company}")
                print(f"   关键词: {latest.position_keyword}")
                print(f"   薪资估算: {latest.salary_estimate or '未知'}")
                print(f"   面试难度: {latest.interview_difficulty or '未知'}")
                print(f"   综合评价: {latest.overall_sentiment}")


async def show_database_stats():
    """Show database statistics."""
    print("\n" + "=" * 60)
    print("📊 数据库统计")
    print("=" * 60)

    db = DatabaseManager(db_path="data/test_etl.db")

    with db.session() as session:
        job_repo = JobRepository(session)
        insight_repo = InsightRepository(session)
        target_repo = CrawlTargetRepository(session)

        print(f"\n总岗位数: {job_repo.count()}")
        print(f"总情报数: {insight_repo.count()}")
        print(f"抓取目标数: {len(target_repo.list_all())}")

        # List companies
        from sqlalchemy import select, distinct
        from offer_sherlock.database.models import Job

        stmt = select(distinct(Job.company))
        companies = list(session.scalars(stmt))
        print(f"\n已收录公司: {', '.join(companies)}")


async def main():
    """Run full ETL integration test."""
    print("🚀 Offer-Sherlock ETL Pipeline 集成测试")
    print("   完整流程: Extract → Transform → Load\n")

    try:
        await test_job_etl()
    except Exception as e:
        print(f"❌ Job ETL 失败: {e}")
        import traceback
        traceback.print_exc()

    try:
        await test_insight_etl()
    except Exception as e:
        print(f"❌ Insight ETL 失败: {e}")
        import traceback
        traceback.print_exc()

    await show_database_stats()

    print("\n✅ ETL 集成测试完成")
    print(f"   数据库文件: data/test_etl.db")


if __name__ == "__main__":
    asyncio.run(main())
