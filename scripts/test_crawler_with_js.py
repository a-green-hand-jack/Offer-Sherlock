#!/usr/bin/env python3
"""Test crawler with JavaScript execution and wait conditions."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from offer_sherlock.crawlers import OfficialCrawler


async def test_bytedance_with_wait():
    """Test ByteDance with wait and scroll."""
    print("🕷️ Testing ByteDance with JavaScript wait/scroll\n")

    crawler = OfficialCrawler(verbose=True)

    # JavaScript to scroll and wait for content
    js_code = """
    // Scroll to trigger lazy loading
    window.scrollTo(0, document.body.scrollHeight / 2);
    await new Promise(r => setTimeout(r, 2000));
    window.scrollTo(0, document.body.scrollHeight);
    await new Promise(r => setTimeout(r, 2000));
    """

    # Wait for job items to appear
    wait_for = "js:() => document.querySelectorAll('.position-item, .job-item, [class*=position], [class*=job]').length > 0"

    result = await crawler.crawl(
        "https://jobs.bytedance.com/campus/position",
        js_code=js_code,
        wait_for=wait_for,
        timeout=90000,
    )

    print(f"\nSuccess: {result.success}")
    print(f"Markdown length: {len(result.markdown)} chars")

    if result.markdown:
        # Save to file
        with open("data/mock/bytedance_positions.md", "w") as f:
            f.write(result.markdown)
        print(f"Saved to data/mock/bytedance_positions.md")

        print(f"\n--- Markdown Content ---")
        print(result.markdown[:3000])
        print("--- End ---")

    return result


async def test_tencent_positions():
    """Test Tencent job positions page."""
    print("\n" + "=" * 60)
    print("Testing Tencent Campus Positions")
    print("=" * 60)

    crawler = OfficialCrawler(verbose=True)

    # Tencent campus job search page
    url = "https://careers.tencent.com/search.html?pcid=40001"

    js_code = """
    await new Promise(r => setTimeout(r, 3000));
    window.scrollTo(0, 500);
    await new Promise(r => setTimeout(r, 2000));
    """

    result = await crawler.crawl(
        url,
        js_code=js_code,
        timeout=90000,
    )

    print(f"\nSuccess: {result.success}")
    print(f"Markdown length: {len(result.markdown)} chars")

    if result.markdown:
        with open("data/mock/tencent_positions.md", "w") as f:
            f.write(result.markdown)
        print(f"Saved to data/mock/tencent_positions.md")

        print(f"\n--- Markdown Preview (first 3000 chars) ---")
        print(result.markdown[:3000])
        print("--- End ---")

    return result


async def test_alibaba_positions():
    """Test Alibaba positions."""
    print("\n" + "=" * 60)
    print("Testing Alibaba Campus Positions")
    print("=" * 60)

    crawler = OfficialCrawler(verbose=True)

    url = "https://talent.alibaba.com/off-campus/position-list?lang=zh"

    js_code = """
    await new Promise(r => setTimeout(r, 3000));
    """

    result = await crawler.crawl(
        url,
        js_code=js_code,
        timeout=90000,
    )

    print(f"\nSuccess: {result.success}")
    print(f"Markdown length: {len(result.markdown)} chars")

    if result.markdown:
        with open("data/mock/alibaba_positions.md", "w") as f:
            f.write(result.markdown)
        print(f"Saved to data/mock/alibaba_positions.md")

        print(f"\n--- Markdown Preview ---")
        print(result.markdown[:3000])
        print("--- End ---")

    return result


if __name__ == "__main__":
    asyncio.run(test_bytedance_with_wait())
    asyncio.run(test_tencent_positions())
    # asyncio.run(test_alibaba_positions())
