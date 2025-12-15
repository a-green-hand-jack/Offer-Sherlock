#!/usr/bin/env python3
"""Test crawler with real job sites."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from offer_sherlock.crawlers import OfficialCrawler, CrawlTarget


async def test_job_sites():
    """Test crawling real job sites."""
    print("🕷️ Testing Job Site Crawling\n")

    crawler = OfficialCrawler(verbose=True)

    # Test targets - using more accessible pages
    targets = [
        CrawlTarget(
            url="https://jobs.bytedance.com/campus",
            company="ByteDance",
            metadata={"type": "campus"},
        ),
        CrawlTarget(
            url="https://careers.tencent.com/",
            company="Tencent",
            metadata={"type": "main"},
        ),
    ]

    for target in targets:
        print("=" * 60)
        print(f"Testing: {target.company}")
        print(f"URL: {target.url}")
        print("=" * 60)

        result = await crawler.crawl_target(target)

        print(f"Success: {result.success}")
        print(f"Markdown length: {len(result.markdown)} chars")

        if result.error:
            print(f"Error: {result.error[:500]}")

        if result.success and result.markdown:
            print(f"\n--- Markdown Preview (first 1500 chars) ---")
            print(result.markdown[:1500])
            print("--- End Preview ---")

            # Save full markdown to file for inspection
            output_file = f"data/mock/{target.company.lower()}_page.md"
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, "w") as f:
                f.write(f"# {target.company} Career Page\n\n")
                f.write(f"URL: {target.url}\n")
                f.write(f"Crawled at: {result.crawled_at}\n\n")
                f.write("---\n\n")
                f.write(result.markdown)
            print(f"\nFull markdown saved to: {output_file}")

        print()


async def test_specific_job_page():
    """Test crawling a specific job listing page."""
    print("=" * 60)
    print("Testing specific job page crawl")
    print("=" * 60)

    crawler = OfficialCrawler(verbose=True)

    # Try a more static job listing page
    url = "https://www.microsoft.com/en-us/research/group/natural-language-computing/"

    result = await crawler.crawl(url, timeout=60000)

    print(f"URL: {result.url}")
    print(f"Success: {result.success}")
    print(f"Markdown length: {len(result.markdown)} chars")

    if result.success and result.markdown:
        print(f"\n--- Markdown Preview ---")
        print(result.markdown[:2000])
        print("--- End Preview ---")


if __name__ == "__main__":
    asyncio.run(test_job_sites())
    # asyncio.run(test_specific_job_page())
