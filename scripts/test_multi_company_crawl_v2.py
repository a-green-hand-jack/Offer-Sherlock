#!/usr/bin/env python3
"""Test crawling multiple company career pages - v2 with optimized targets."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from offer_sherlock.crawlers import OfficialCrawler, CrawlTarget


# Optimized crawl targets with wait conditions and JS execution
CRAWL_TARGETS = [
    # 国内大厂 - 优化后的URL和等待策略
    CrawlTarget(
        url="https://jobs.bytedance.com/campus/position",
        company="字节跳动",
        wait_for="css:.position-list, .job-card",  # Wait for job list to load
        js_code="window.scrollTo(0, 1000); await new Promise(r => setTimeout(r, 2000));",
        metadata={"region": "China", "type": "campus"},
    ),
    CrawlTarget(
        url="https://careers.tencent.com/search.html?pcid=40001",
        company="腾讯",
        wait_for="css:.recruit-list",
        metadata={"region": "China", "type": "campus"},
    ),
    CrawlTarget(
        url="https://talent.alibaba.com/off-campus/position-list",
        company="阿里巴巴(社招)",
        wait_for="css:.position-item, .job-list",
        js_code="window.scrollTo(0, 500);",
        metadata={"region": "China", "type": "social"},
    ),
    CrawlTarget(
        url="https://xiaomi.jobs.feishu.cn/",
        company="小米(飞书)",
        wait_for="css:.job-card",
        metadata={"region": "China", "type": "campus"},
    ),
    CrawlTarget(
        url="https://career.huawei.com/reccampportal/portal5/campus-recruitment.html",
        company="华为",
        wait_for="css:.job-list, .position-item",
        metadata={"region": "China", "type": "campus"},
    ),
    CrawlTarget(
        url="https://talent.baidu.com/jobs/list",
        company="百度",
        wait_for="css:.job-item, .position-list",
        metadata={"region": "China", "type": "social"},
    ),
    CrawlTarget(
        url="https://zhaopin.meituan.com/web/position?jobFamily=1",
        company="美团",
        wait_for="css:.position-item",
        metadata={"region": "China", "type": "social"},
    ),
    CrawlTarget(
        url="https://careers.jd.com/",
        company="京东",
        metadata={"region": "China", "type": "campus"},
    ),
    CrawlTarget(
        url="https://join.qq.com/post.html",
        company="腾讯(校招)",
        wait_for="css:.recruit-item",
        metadata={"region": "China", "type": "campus"},
    ),
    # 国际大厂
    CrawlTarget(
        url="https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
        company="NVIDIA(Workday)",
        wait_for="css:[data-automation-id='jobResults']",
        metadata={"region": "US", "type": "social"},
    ),
    CrawlTarget(
        url="https://www.google.com/about/careers/applications/jobs/results/",
        company="Google",
        wait_for="css:.gc-card",
        metadata={"region": "US", "type": "social"},
    ),
    CrawlTarget(
        url="https://jobs.careers.microsoft.com/global/en/search",
        company="Microsoft",
        wait_for="css:.ms-List-cell",
        js_code="window.scrollTo(0, 500);",
        metadata={"region": "US", "type": "social"},
    ),
    CrawlTarget(
        url="https://www.metacareers.com/jobs?teams[0]=Internship%20-%20Engineering%2C%20Tech%20%26%20Design",
        company="Meta(实习)",
        wait_for="css:[role='listitem']",
        js_code="window.scrollTo(0, 1000);",
        metadata={"region": "US", "type": "internship"},
    ),
    CrawlTarget(
        url="https://jobs.apple.com/en-us/search?sort=relevance&key=software%20engineer",
        company="Apple",
        wait_for="css:.results__table",
        metadata={"region": "US", "type": "social"},
    ),
    CrawlTarget(
        url="https://www.amazon.jobs/en/search?offset=0&result_limit=10&sort=relevant&category[]=software-development",
        company="Amazon(软件开发)",
        wait_for="css:.job-tile",
        metadata={"region": "US", "type": "social"},
    ),
    CrawlTarget(
        url="https://careers.openai.com/",
        company="OpenAI",
        wait_for="css:.opening",
        metadata={"region": "US", "type": "social"},
    ),
]


async def test_single_target(crawler: OfficialCrawler, target: CrawlTarget, timeout: int = 60000) -> dict:
    """Test crawling a single target."""
    print(f"\n{'='*60}")
    print(f"🔍 Crawling: {target.company}")
    print(f"   URL: {target.url[:60]}...")
    print(f"{'='*60}")

    try:
        result = await crawler.crawl(
            url=target.url,
            css_selector=target.css_selector,
            wait_for=target.wait_for,
            js_code=target.js_code,
            timeout=timeout,
        )

        # Add company metadata
        result.metadata["company"] = target.company
        result.metadata.update(target.metadata)

        status = "✅ Success" if result.success else "❌ Failed"
        content_len = len(result.markdown) if result.markdown else 0

        print(f"   Status: {status}")
        print(f"   Content Length: {content_len} chars")

        if result.error:
            print(f"   Error: {result.error[:100]}...")

        # Show preview of content (more meaningful portion)
        if result.markdown and content_len > 100:
            # Try to find job-related content
            preview = result.markdown[:800].replace("\n", " ")[:300]
            print(f"   Preview: {preview}...")

        return {
            "company": target.company,
            "url": target.url,
            "success": result.success,
            "content_length": content_len,
            "error": result.error,
            "region": target.metadata.get("region"),
            "markdown": result.markdown if result.success else None,
        }
    except Exception as e:
        print(f"   Exception: {str(e)[:100]}...")
        return {
            "company": target.company,
            "url": target.url,
            "success": False,
            "content_length": 0,
            "error": str(e),
            "region": target.metadata.get("region"),
            "markdown": None,
        }


async def main():
    """Test crawling all company targets."""
    print("🕷️ Multi-Company Career Page Crawl Test v2")
    print(f"Testing {len(CRAWL_TARGETS)} targets with optimized settings...\n")

    crawler = OfficialCrawler(verbose=False, headless=True)

    results = []
    for target in CRAWL_TARGETS:
        result = await test_single_target(crawler, target, timeout=60000)
        results.append(result)
        # Small delay between requests
        await asyncio.sleep(2)

    # Summary
    print("\n" + "="*70)
    print("📊 SUMMARY")
    print("="*70)

    success_count = sum(1 for r in results if r["success"] and r["content_length"] > 100)
    partial_count = sum(1 for r in results if r["success"] and r["content_length"] <= 100)
    failed_count = sum(1 for r in results if not r["success"])

    print(f"\nTotal: {len(results)} | Good: {success_count} | Partial: {partial_count} | Failed: {failed_count}")

    print("\n📈 Results by Company:\n")
    print(f"{'Company':<20} {'Region':<8} {'Status':<10} {'Content':<12}")
    print("-" * 60)

    for r in results:
        if r["success"] and r["content_length"] > 500:
            status = "✅ Good"
        elif r["success"] and r["content_length"] > 100:
            status = "⚠️ Partial"
        elif r["success"]:
            status = "❌ Empty"
        else:
            status = "❌ Error"
        content = f"{r['content_length']:,} chars" if r["content_length"] > 0 else "-"
        print(f"{r['company']:<20} {r['region']:<8} {status:<10} {content:<12}")

    # Save good results
    print("\n💾 Saving successful crawl results...")
    os.makedirs("data/crawl_results", exist_ok=True)

    for r in results:
        if r["success"] and r["content_length"] > 500 and r["markdown"]:
            safe_name = r["company"].replace("/", "_").replace("(", "_").replace(")", "")
            filepath = f"data/crawl_results/{safe_name}.md"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {r['company']}\n\n")
                f.write(f"URL: {r['url']}\n\n")
                f.write(f"---\n\n")
                f.write(r["markdown"])
            print(f"   Saved: {filepath}")

    print("\n✅ Done!")


if __name__ == "__main__":
    asyncio.run(main())
