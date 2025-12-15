#!/usr/bin/env python3
"""Test crawling multiple company career pages - v3 simpler approach."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from offer_sherlock.crawlers import OfficialCrawler, CrawlTarget


# Simpler crawl targets without wait_for (let pages load naturally)
CRAWL_TARGETS = [
    # 国内大厂
    CrawlTarget(url="https://jobs.bytedance.com/campus/position", company="字节跳动", metadata={"region": "China"}),
    CrawlTarget(url="https://careers.tencent.com/search.html?pcid=40001", company="腾讯", metadata={"region": "China"}),
    CrawlTarget(url="https://talent.alibaba.com/off-campus/position-list", company="阿里巴巴", metadata={"region": "China"}),
    CrawlTarget(url="https://career.huawei.com/reccampportal/portal5/campus-recruitment.html", company="华为", metadata={"region": "China"}),
    CrawlTarget(url="https://talent.baidu.com/jobs/list", company="百度", metadata={"region": "China"}),
    CrawlTarget(url="https://zhaopin.meituan.com/web/position", company="美团", metadata={"region": "China"}),
    CrawlTarget(url="https://careers.jd.com/", company="京东", metadata={"region": "China"}),
    CrawlTarget(url="https://join.qq.com/", company="腾讯校招", metadata={"region": "China"}),
    CrawlTarget(url="https://app.mokahr.com/campus-recruitment/bytedancecampus", company="字节Moka", metadata={"region": "China"}),
    CrawlTarget(url="https://hr.didi.com/", company="滴滴", metadata={"region": "China"}),
    CrawlTarget(url="https://app.mokahr.com/campus-recruitment/bilikibi", company="B站", metadata={"region": "China"}),
    CrawlTarget(url="https://career.pinduoduo.com/", company="拼多多", metadata={"region": "China"}),

    # 国际大厂
    CrawlTarget(url="https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite", company="NVIDIA", metadata={"region": "US"}),
    CrawlTarget(url="https://careers.google.com/jobs/results/", company="Google", metadata={"region": "US"}),
    CrawlTarget(url="https://careers.microsoft.com/v2/global/en/search", company="Microsoft", metadata={"region": "US"}),
    CrawlTarget(url="https://www.metacareers.com/jobs", company="Meta", metadata={"region": "US"}),
    CrawlTarget(url="https://jobs.apple.com/en-us/search", company="Apple", metadata={"region": "US"}),
    CrawlTarget(url="https://www.amazon.jobs/en/search?category[]=software-development", company="Amazon", metadata={"region": "US"}),
    CrawlTarget(url="https://openai.com/careers", company="OpenAI", metadata={"region": "US"}),
    CrawlTarget(url="https://www.linkedin.com/jobs/", company="LinkedIn", metadata={"region": "US"}),
    CrawlTarget(url="https://www.tesla.com/careers/search", company="Tesla", metadata={"region": "US"}),
    CrawlTarget(url="https://www.uber.com/us/en/careers/", company="Uber", metadata={"region": "US"}),
]


async def test_single_target(crawler: OfficialCrawler, target: CrawlTarget, timeout: int = 30000) -> dict:
    """Test crawling a single target."""
    print(f"\n{'='*60}")
    print(f"🔍 {target.company}")
    print(f"   {target.url[:55]}...")
    print(f"{'='*60}")

    try:
        result = await crawler.crawl(url=target.url, timeout=timeout)
        result.metadata["company"] = target.company
        result.metadata.update(target.metadata)

        content_len = len(result.markdown) if result.markdown else 0
        status = "✅" if result.success and content_len > 500 else ("⚠️" if result.success else "❌")

        print(f"   {status} {content_len:,} chars")

        if result.error:
            print(f"   Error: {result.error[:80]}...")

        if result.markdown and content_len > 100:
            preview = result.markdown[:300].replace("\n", " ")[:150]
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
        print(f"   ❌ Exception: {str(e)[:80]}...")
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
    print("🕷️ Multi-Company Career Page Crawl Test v3")
    print(f"Testing {len(CRAWL_TARGETS)} targets (no wait conditions)...\n")

    crawler = OfficialCrawler(verbose=False, headless=True)

    results = []
    for target in CRAWL_TARGETS:
        result = await test_single_target(crawler, target, timeout=30000)
        results.append(result)
        await asyncio.sleep(1)

    # Summary
    print("\n" + "="*70)
    print("📊 FINAL SUMMARY")
    print("="*70)

    good = [r for r in results if r["success"] and r["content_length"] > 500]
    partial = [r for r in results if r["success"] and r["content_length"] <= 500]
    failed = [r for r in results if not r["success"]]

    print(f"\n✅ Good ({len(good)}): {', '.join(r['company'] for r in good)}")
    print(f"⚠️ Partial ({len(partial)}): {', '.join(r['company'] for r in partial)}")
    print(f"❌ Failed ({len(failed)}): {', '.join(r['company'] for r in failed)}")

    # Detailed table
    print("\n" + "-"*70)
    print(f"{'Company':<15} {'Region':<8} {'Status':<10} {'Content':<12}")
    print("-"*70)

    for r in sorted(results, key=lambda x: -x["content_length"]):
        if r["success"] and r["content_length"] > 500:
            status = "✅ Good"
        elif r["success"] and r["content_length"] > 0:
            status = "⚠️ Partial"
        else:
            status = "❌ Failed"
        content = f"{r['content_length']:,}" if r["content_length"] > 0 else "-"
        print(f"{r['company']:<15} {r['region']:<8} {status:<10} {content:<12}")

    # Save good results
    print("\n💾 Saving results to data/crawl_results/...")
    os.makedirs("data/crawl_results", exist_ok=True)

    for r in results:
        if r["success"] and r["content_length"] > 500 and r["markdown"]:
            safe_name = r["company"].replace("/", "_").replace("(", "_").replace(")", "")
            filepath = f"data/crawl_results/{safe_name}.md"
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(f"# {r['company']}\n\nURL: {r['url']}\n\n---\n\n{r['markdown']}")
            print(f"   ✓ {safe_name}.md ({r['content_length']:,} chars)")


if __name__ == "__main__":
    asyncio.run(main())
