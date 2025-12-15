#!/usr/bin/env python3
"""Test crawler + LLM extraction pipeline."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pydantic import BaseModel, Field
from typing import Optional, List

from offer_sherlock.crawlers import OfficialCrawler
from offer_sherlock.llm import LLMClient, LLMProvider


class JobListing(BaseModel):
    """Extracted job listing information."""
    title: str = Field(description="职位名称")
    company: str = Field(description="公司名称")
    location: Optional[str] = Field(default=None, description="工作地点")
    job_type: Optional[str] = Field(default=None, description="职位类型（校招/社招/实习）")
    requirements: Optional[str] = Field(default=None, description="职位要求摘要")
    salary_range: Optional[str] = Field(default=None, description="薪资范围（如有）")


class PageJobListings(BaseModel):
    """Multiple job listings from a page."""
    company: str = Field(description="公司名称")
    total_jobs_found: int = Field(description="页面上找到的职位总数")
    jobs: List[JobListing] = Field(description="职位列表（最多5个）")
    page_summary: str = Field(description="页面内容摘要")


async def test_crawl_and_extract():
    """Test crawling and LLM extraction."""
    print("🕷️ + 🤖 Crawler + LLM Extraction Test\n")

    # Initialize
    crawler = OfficialCrawler(verbose=False)
    llm = LLMClient(provider=LLMProvider.QWEN)

    print(f"LLM: {llm}")

    # Crawl ByteDance jobs page
    print("\n" + "=" * 60)
    print("Step 1: Crawling ByteDance Campus Page")
    print("=" * 60)

    result = await crawler.crawl(
        "https://jobs.bytedance.com/campus/position",
        timeout=60000,
    )

    print(f"Success: {result.success}")
    print(f"Markdown length: {len(result.markdown)} chars")

    if not result.success:
        print(f"Error: {result.error}")
        return

    # Limit markdown to avoid token overflow
    markdown_preview = result.markdown[:8000]

    print("\n" + "=" * 60)
    print("Step 2: LLM Extraction")
    print("=" * 60)

    system_prompt = """你是一个专业的招聘信息提取助手。
你的任务是从网页内容中提取结构化的职位信息。
- 仔细分析提供的 Markdown 内容
- 提取所有能找到的职位信息
- 如果某些字段无法确定，设为 null
- 只提取前5个职位作为示例
- 用中文填写所有字段"""

    user_message = f"""请从以下字节跳动招聘页面内容中提取职位信息：

---
{markdown_preview}
---

请提取页面中的职位列表，包括职位名称、工作地点、职位类型等信息。"""

    print("Extracting job listings with LLM...")

    try:
        extracted = llm.chat_structured(
            user_message,
            output_schema=PageJobListings,
            system_prompt=system_prompt,
        )

        print(f"\n✅ Extraction successful!")
        print(f"\nCompany: {extracted.company}")
        print(f"Total jobs found: {extracted.total_jobs_found}")
        print(f"Page summary: {extracted.page_summary}")
        print(f"\nExtracted {len(extracted.jobs)} job listings:")

        for i, job in enumerate(extracted.jobs, 1):
            print(f"\n  [{i}] {job.title}")
            print(f"      Company: {job.company}")
            print(f"      Location: {job.location}")
            print(f"      Type: {job.job_type}")
            if job.requirements:
                print(f"      Requirements: {job.requirements[:100]}...")
            if job.salary_range:
                print(f"      Salary: {job.salary_range}")

    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()

        # Fallback to simple chat
        print("\nFallback to simple chat...")
        response = llm.chat(
            f"请简要总结这个招聘页面的内容，列出你能找到的职位名称：\n\n{markdown_preview[:4000]}",
            system_prompt="你是一个招聘信息分析助手，请用中文回答。"
        )
        print(f"\nLLM Response:\n{response}")


if __name__ == "__main__":
    # Set API key
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("Please set DASHSCOPE_API_KEY environment variable")
        sys.exit(1)

    asyncio.run(test_crawl_and_extract())
