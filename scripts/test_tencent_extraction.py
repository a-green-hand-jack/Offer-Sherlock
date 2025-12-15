#!/usr/bin/env python3
"""Test LLM extraction with Tencent job data."""

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
    department: Optional[str] = Field(default=None, description="部门/事业群")
    experience: Optional[str] = Field(default=None, description="工作经验要求")
    location: Optional[str] = Field(default=None, description="工作地点")
    job_type: Optional[str] = Field(default=None, description="招聘类型（社招/校招/实习）")
    description: Optional[str] = Field(default=None, description="职位描述摘要（50字以内）")
    update_date: Optional[str] = Field(default=None, description="更新日期")


class ExtractedJobs(BaseModel):
    """Extracted job listings from page."""
    company: str = Field(description="公司名称")
    total_positions: int = Field(description="页面显示的职位总数")
    jobs: List[JobListing] = Field(description="提取的职位列表")


async def main():
    """Test extraction pipeline."""
    print("🕷️ + 🤖 Tencent Job Extraction Test\n")

    # Read saved markdown
    markdown_file = "data/mock/tencent_positions.md"
    if os.path.exists(markdown_file):
        with open(markdown_file, "r") as f:
            markdown_content = f.read()
        print(f"Loaded cached markdown: {len(markdown_content)} chars")
    else:
        # Crawl fresh
        print("Crawling Tencent positions...")
        crawler = OfficialCrawler(verbose=True)
        result = await crawler.crawl(
            "https://careers.tencent.com/search.html?pcid=40001",
            timeout=90000,
        )
        markdown_content = result.markdown
        print(f"Crawled: {len(markdown_content)} chars")

    # Initialize LLM
    llm = LLMClient(provider=LLMProvider.QWEN)
    print(f"LLM: {llm}\n")

    # Extract jobs
    print("=" * 60)
    print("Extracting jobs with LLM...")
    print("=" * 60)

    system_prompt = """你是一个专业的招聘信息提取助手。
请从网页内容中提取职位信息。注意：
1. 仔细识别每个职位的标题、部门、经验要求、地点等信息
2. 职位描述请简要概括（50字以内）
3. 提取页面显示的所有职位（最多10个）
4. 如果某些字段无法确定，设为 null"""

    # Use relevant portion of markdown
    relevant_content = markdown_content[-5000:]  # Job listings are usually at the end

    user_message = f"""请从以下腾讯招聘页面内容中提取职位信息：

---
{relevant_content}
---

请提取所有能找到的职位信息。"""

    try:
        extracted = llm.chat_structured(
            user_message,
            output_schema=ExtractedJobs,
            system_prompt=system_prompt,
        )

        print(f"\n✅ Extraction successful!")
        print(f"\nCompany: {extracted.company}")
        print(f"Total positions on page: {extracted.total_positions}")
        print(f"\nExtracted {len(extracted.jobs)} jobs:\n")

        for i, job in enumerate(extracted.jobs, 1):
            print(f"[{i}] {job.title}")
            print(f"    Department: {job.department}")
            print(f"    Experience: {job.experience}")
            print(f"    Location: {job.location}")
            print(f"    Type: {job.job_type}")
            print(f"    Updated: {job.update_date}")
            if job.description:
                print(f"    Description: {job.description}")
            print()

    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("Please set DASHSCOPE_API_KEY")
        sys.exit(1)

    asyncio.run(main())
