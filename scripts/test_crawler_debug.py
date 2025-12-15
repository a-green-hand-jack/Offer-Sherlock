#!/usr/bin/env python3
"""Debug crawler issues."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


async def test_crawl4ai_direct():
    """Test Crawl4AI directly to see errors."""
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

    print("Testing Crawl4AI directly...")

    browser_config = BrowserConfig(
        headless=True,
        verbose=True,
    )

    run_config = CrawlerRunConfig(
        page_timeout=60000,
    )

    # Try different URLs
    test_urls = [
        "https://httpbin.org/html",
        "https://www.bing.com",
        "https://github.com",
    ]

    try:
        async with AsyncWebCrawler(config=browser_config) as crawler:
            print("Crawler initialized successfully!\n")

            for url in test_urls:
                print(f"Testing URL: {url}")
                print("-" * 40)

                try:
                    result = await crawler.arun(url=url, config=run_config)

                    print(f"  Success: {result.success}")
                    print(f"  Markdown length: {len(result.markdown) if result.markdown else 0}")

                    if result.success and result.markdown:
                        preview = result.markdown[:300].replace('\n', ' ')
                        print(f"  Preview: {preview}...")
                    elif not result.success:
                        error = getattr(result, 'error_message', 'Unknown error')
                        print(f"  Error: {error[:200] if error else 'None'}")

                except Exception as e:
                    print(f"  Exception: {str(e)[:200]}")

                print()

    except Exception as e:
        print(f"Crawler init exception: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_crawl4ai_direct())
