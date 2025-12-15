#!/usr/bin/env python3
"""Test crawling multiple company career pages."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from offer_sherlock.crawlers import OfficialCrawler, CrawlTarget


# Define crawl targets for major tech companies
CRAWL_TARGETS = [
    # 国内大厂
    CrawlTarget(
        url="https://jobs.bytedance.com/campus/position",
        company="字节跳动",
        metadata={"region": "China", "type": "campus"},
    ),
    CrawlTarget(
        url="https://careers.tencent.com/search.html?pcid=40001",
        company="腾讯",
        metadata={"region": "China", "type": "campus"},
    ),
    CrawlTarget(
        url="https://talent.alibaba.com/campus/home",
        company="阿里巴巴",
        metadata={"region": "China", "type": "campus"},
    ),
    CrawlTarget(
        url="https://app.mokahr.com/campus-recruitment/xiaomi",
        company="小米",
        metadata={"region": "China", "type": "campus"},
    ),
    CrawlTarget(
        url="https://career.huawei.com/reccampportal/portal5/campus-recruitment.html",
        company="华为",
        metadata={"region": "China", "type": "campus"},
    ),
    CrawlTarget(
        url="https://careers.baidu.com/jobs/list",
        company="百度",
        metadata={"region": "China", "type": "social"},
    ),
    CrawlTarget(
        url="https://hr.meituan.com/web/position/list",
        company="美团",
        metadata={"region": "China", "type": "social"},
    ),
    # 国际大厂
    CrawlTarget(
        url="https://www.nvidia.com/en-us/about-nvidia/careers/",
        company="NVIDIA",
        metadata={"region": "US", "type": "social"},
    ),
    CrawlTarget(
        url="https://careers.google.com/jobs/results/",
        company="Google",
        metadata={"region": "US", "type": "social"},
    ),
    CrawlTarget(
        url="https://careers.microsoft.com/v2/global/en/search",
        company="Microsoft",
        metadata={"region": "US", "type": "social"},
    ),
    CrawlTarget(
        url="https://www.metacareers.com/jobs",
        company="Meta",
        metadata={"region": "US", "type": "social"},
    ),
    CrawlTarget(
        url="https://www.apple.com/careers/us/",
        company="Apple",
        metadata={"region": "US", "type": "social"},
    ),
    CrawlTarget(
        url="https://www.amazon.jobs/en/",
        company="Amazon",
        metadata={"region": "US", "type": "social"},
    ),
]


async def test_single_target(crawler: OfficialCrawler, target: CrawlTarget) -> dict:
    """Test crawling a single target."""
    print(f"\n{'='*60}")
    print(f"🔍 Crawling: {target.company}")
    print(f"   URL: {target.url}")
    print(f"{'='*60}")

    try:
        result = await crawler.crawl_target(target)

        status = "✅ Success" if result.success else "❌ Failed"
        content_len = len(result.markdown) if result.markdown else 0

        print(f"   Status: {status}")
        print(f"   Content Length: {content_len} chars")

        if result.error:
            print(f"   Error: {result.error}")

        # Show preview of content
        if result.markdown and content_len > 0:
            preview = result.markdown[:500].replace("\n", " ")[:200]
            print(f"   Preview: {preview}...")

        return {
            "company": target.company,
            "url": target.url,
            "success": result.success,
            "content_length": content_len,
            "error": result.error,
            "region": target.metadata.get("region"),
        }
    except Exception as e:
        print(f"   Exception: {e}")
        return {
            "company": target.company,
            "url": target.url,
            "success": False,
            "content_length": 0,
            "error": str(e),
            "region": target.metadata.get("region"),
        }


async def main():
    """Test crawling all company targets."""
    print("🕷️ Multi-Company Career Page Crawl Test")
    print(f"Testing {len(CRAWL_TARGETS)} targets...\n")

    crawler = OfficialCrawler(verbose=False, headless=True)

    results = []
    for target in CRAWL_TARGETS:
        result = await test_single_target(crawler, target)
        results.append(result)
        # Small delay between requests
        await asyncio.sleep(1)

    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)

    success_count = sum(1 for r in results if r["success"])
    print(f"\nTotal: {len(results)} | Success: {success_count} | Failed: {len(results) - success_count}")

    print("\n📈 Results by Company:\n")
    print(f"{'Company':<15} {'Region':<8} {'Status':<10} {'Content':<12} {'Error'}")
    print("-" * 80)

    for r in results:
        status = "✅" if r["success"] else "❌"
        content = f"{r['content_length']:,} chars" if r["content_length"] > 0 else "-"
        error = (r["error"][:30] + "...") if r["error"] and len(r["error"]) > 30 else (r["error"] or "-")
        print(f"{r['company']:<15} {r['region']:<8} {status:<10} {content:<12} {error}")

    # Save successful results
    print("\n💾 Saving successful crawl results...")
    os.makedirs("data/crawl_results", exist_ok=True)

    for r in results:
        if r["success"] and r["content_length"] > 500:
            # Re-crawl to save (we didn't store markdown in summary)
            pass  # Will implement if needed


if __name__ == "__main__":
    asyncio.run(main())
