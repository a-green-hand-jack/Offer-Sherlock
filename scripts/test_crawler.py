#!/usr/bin/env python3
"""Test crawler with real job sites."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from offer_sherlock.crawlers import OfficialCrawler, CrawlTarget


async def test_simple_crawl():
    """Test basic crawling without selector."""
    print("=" * 60)
    print("Test 1: Simple crawl (no selector)")
    print("=" * 60)

    crawler = OfficialCrawler(verbose=True)

    # Test with a simple page first
    result = await crawler.crawl("https://example.com")

    print(f"URL: {result.url}")
    print(f"Success: {result.success}")
    print(f"Title: {result.title}")
    print(f"Markdown length: {len(result.markdown)} chars")
    print(f"Markdown preview:\n{result.markdown[:500]}...")
    print()

    return result.success


async def test_bytedance_jobs():
    """Test crawling ByteDance jobs page."""
    print("=" * 60)
    print("Test 2: ByteDance Campus Recruitment")
    print("=" * 60)

    crawler = OfficialCrawler(verbose=True)

    # ByteDance campus recruitment page
    url = "https://jobs.bytedance.com/campus/position"

    result = await crawler.crawl(
        url=url,
        wait_for="css:.position-item",  # Wait for job items to load
        timeout=60000,
    )

    print(f"URL: {result.url}")
    print(f"Success: {result.success}")
    if result.error:
        print(f"Error: {result.error}")
    print(f"Markdown length: {len(result.markdown)} chars")

    if result.markdown:
        print(f"\nMarkdown preview (first 1000 chars):\n")
        print("-" * 40)
        print(result.markdown[:1000])
        print("-" * 40)

    return result.success


async def test_alibaba_jobs():
    """Test crawling Alibaba jobs page."""
    print("=" * 60)
    print("Test 3: Alibaba Campus Recruitment")
    print("=" * 60)

    crawler = OfficialCrawler(verbose=True)

    # Alibaba campus recruitment
    url = "https://talent.alibaba.com/campus/home"

    result = await crawler.crawl(
        url=url,
        timeout=60000,
    )

    print(f"URL: {result.url}")
    print(f"Success: {result.success}")
    if result.error:
        print(f"Error: {result.error}")
    print(f"Markdown length: {len(result.markdown)} chars")

    if result.markdown:
        print(f"\nMarkdown preview (first 1000 chars):\n")
        print("-" * 40)
        print(result.markdown[:1000])
        print("-" * 40)

    return result.success


async def test_with_targets():
    """Test crawling with CrawlTarget configuration."""
    print("=" * 60)
    print("Test 4: Multiple targets with configuration")
    print("=" * 60)

    crawler = OfficialCrawler(verbose=True)

    targets = [
        CrawlTarget(
            url="https://example.com",
            company="Example Corp",
            metadata={"type": "test"},
        ),
    ]

    results = await crawler.crawl_targets(targets)

    for result in results:
        print(f"Company: {result.metadata.get('company')}")
        print(f"URL: {result.url}")
        print(f"Success: {result.success}")
        print(f"Markdown length: {len(result.markdown)} chars")
        print()

    return all(r.success for r in results)


async def main():
    """Run all crawler tests."""
    print("\n🕷️ Offer-Sherlock Crawler Tests\n")

    tests = [
        ("Simple crawl", test_simple_crawl),
        ("CrawlTarget test", test_with_targets),
        # ("ByteDance Jobs", test_bytedance_jobs),  # May need JS handling
        # ("Alibaba Jobs", test_alibaba_jobs),       # May need JS handling
    ]

    results = []
    for name, test_func in tests:
        try:
            success = await test_func()
            results.append((name, success, None))
        except Exception as e:
            results.append((name, False, str(e)))
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    for name, success, error in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {name}")
        if error:
            print(f"       Error: {error}")

    return all(r[1] for r in results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
