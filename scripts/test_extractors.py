#!/usr/bin/env python3
"""Integration test for extractors using real data and Qwen-plus LLM."""

import asyncio
from pathlib import Path

from offer_sherlock.extractors import JobExtractor, InsightExtractor
from offer_sherlock.crawlers import XhsCrawler
from offer_sherlock.llm.client import LLMClient
from offer_sherlock.utils.config import LLMProvider


async def test_job_extractor():
    """Test JobExtractor with real crawled data."""
    print("=" * 60)
    print("🧪 测试 JobExtractor - 从官网内容提取岗位信息")
    print("=" * 60)

    # Read sample crawled content
    data_dir = Path(__file__).parent.parent / "data" / "crawl_results"

    # Test with Apple jobs page
    apple_file = data_dir / "Apple.md"
    if apple_file.exists():
        print(f"\n📖 读取: {apple_file.name}")
        content = apple_file.read_text()[:10000]  # Limit content size

        # Create extractor with Qwen-plus
        llm = LLMClient(provider=LLMProvider.QWEN, model="qwen-plus")
        extractor = JobExtractor(llm_client=llm)

        print("🤖 使用 Qwen-plus 提取岗位信息...")
        result = await extractor.extract(
            content=content,
            company="Apple",
            source_url="https://jobs.apple.com/en-us/search",
        )

        print(f"\n✅ 提取结果: 找到 {result.count} 个岗位")
        for i, job in enumerate(result.jobs[:5], 1):
            print(f"\n[{i}] {job.title}")
            print(f"    公司: {job.company}")
            print(f"    地点: {job.location or '未知'}")
            print(f"    类型: {job.job_type or '未知'}")
            print(f"    ID: {job.job_id_external or '未知'}")
            if job.requirements:
                print(f"    要求: {job.requirements[:80]}...")

        if result.extraction_notes:
            print(f"\n📝 提取说明: {result.extraction_notes}")

    # Test with Chinese company
    print("\n" + "-" * 60)
    huawei_file = data_dir / "华为.md"
    if huawei_file.exists():
        print(f"\n📖 读取: {huawei_file.name}")
        content = huawei_file.read_text()[:10000]

        result = await extractor.extract(
            content=content,
            company="华为",
            source_url="https://career.huawei.com/reccampportal/portal5/campus-recruitment.html",
        )

        print(f"\n✅ 提取结果: 找到 {result.count} 个岗位")
        for i, job in enumerate(result.jobs[:5], 1):
            print(f"\n[{i}] {job.title}")
            print(f"    地点: {job.location or '未知'}")
            print(f"    类型: {job.job_type or '未知'}")


async def test_insight_extractor():
    """Test InsightExtractor with XHS notes."""
    print("\n" + "=" * 60)
    print("🧪 测试 InsightExtractor - 从小红书内容提取情报")
    print("=" * 60)

    # Create XHS crawler and search
    print("\n🔍 搜索小红书: 字节跳动 offer")

    async with XhsCrawler(headless=True) as crawler:
        notes = await crawler.search("字节跳动 offer", max_results=5)

        if not notes:
            print("❌ 未找到笔记，跳过测试")
            return

        print(f"📖 找到 {len(notes)} 条笔记")

        # Create extractor
        llm = LLMClient(provider=LLMProvider.QWEN, model="qwen-plus")
        extractor = InsightExtractor(llm_client=llm)

        # Extract and analyze
        print("\n🤖 使用 Qwen-plus 分析笔记...")
        summary = await extractor.analyze_notes(
            notes=notes,
            company="字节跳动",
            position_keyword="offer",
        )

        # Print results
        print("\n" + "=" * 60)
        print("📊 情报汇总")
        print("=" * 60)
        print(summary.to_markdown())

        print("\n📝 来源帖子:")
        for i, post in enumerate(summary.source_posts[:5], 1):
            sentiment_map = {"positive": "👍", "negative": "👎", "neutral": "➖"}
            emoji = sentiment_map.get(post.sentiment.value, "➖")
            print(f"  [{i}] {emoji} {post.title[:40]}... ({post.likes} 赞)")
            if post.mentioned_salary:
                print(f"       💰 薪资: {post.mentioned_salary}")


async def main():
    """Run all integration tests."""
    print("🚀 Offer-Sherlock 提取器集成测试")
    print("   使用 Qwen-plus 作为 LLM\n")

    try:
        await test_job_extractor()
    except Exception as e:
        print(f"❌ JobExtractor 测试失败: {e}")

    try:
        await test_insight_extractor()
    except Exception as e:
        print(f"❌ InsightExtractor 测试失败: {e}")

    print("\n✅ 集成测试完成")


if __name__ == "__main__":
    asyncio.run(main())
