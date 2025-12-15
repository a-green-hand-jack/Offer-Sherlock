"""Job extractor for official recruitment sites."""

from typing import Optional

from offer_sherlock.extractors.base import BaseExtractor
from offer_sherlock.llm.client import LLMClient
from offer_sherlock.schemas.job import JobListExtraction, JobPosting

# System prompt for job extraction
JOB_EXTRACTION_SYSTEM_PROMPT = """你是一个专业的招聘信息提取助手。你的任务是从招聘网站的页面内容中提取结构化的岗位信息。

## 提取规则

1. **岗位名称 (title)**: 提取完整的职位名称
2. **公司名称 (company)**: 使用提供的公司名，保持一致
3. **外部 ID (job_id_external)**: 从 URL 或页面内容中提取岗位的唯一标识符
4. **工作地点 (location)**: 提取工作城市/地区
5. **岗位类型 (job_type)**: 判断是"校招"、"社招"还是"实习"
6. **核心要求 (requirements)**: 用 1-2 句话总结主要要求
7. **薪资范围 (salary_range)**: 如果页面显示薪资，提取出来；没有则为 null
8. **投递链接 (apply_link)**: 提取申请/投递的链接

## 注意事项

- 如果是岗位列表页，提取所有可见的岗位基本信息
- 如果是岗位详情页，提取该岗位的完整信息
- 没有的信息填 null，不要编造
- 外部 ID 通常是数字或字母数字组合，在 URL 中出现
- 中国公司的校招通常标注"校园招聘"、"应届生"等关键词
- 实习岗位通常包含"实习"、"intern"等关键词"""

JOB_EXTRACTION_USER_PROMPT = """请从以下 {company} 的招聘页面内容中提取岗位信息。

来源 URL: {source_url}

---
页面内容:
{content}
---

请提取所有能识别的岗位信息。如果这是一个列表页，提取每个岗位的基本信息；如果是详情页，提取完整信息。"""


class JobExtractor(BaseExtractor[JobListExtraction]):
    """Extractor for job postings from official recruitment sites.

    Uses LLM to parse raw HTML/Markdown content and extract structured
    job posting information.

    Example:
        >>> extractor = JobExtractor(llm_client)
        >>> result = await extractor.extract(
        ...     content=markdown_content,
        ...     company="字节跳动",
        ...     source_url="https://jobs.bytedance.com/..."
        ... )
        >>> for job in result.jobs:
        ...     print(job.title, job.location)
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        max_content_length: int = 15000,
    ):
        """Initialize the job extractor.

        Args:
            llm_client: LLM client for extraction. Creates default if None.
            max_content_length: Max content length to process.
        """
        if llm_client is None:
            from offer_sherlock.utils.config import LLMProvider

            # Use qwen-max for better structured output parsing
            llm_client = LLMClient(provider=LLMProvider.QWEN, model="qwen-max")
        super().__init__(llm_client, max_content_length)

    async def extract(
        self,
        content: str,
        company: str = "Unknown",
        source_url: str = "",
        **kwargs,
    ) -> JobListExtraction:
        """Extract job postings from page content.

        Args:
            content: Raw Markdown/HTML content from the page.
            company: Company name for context.
            source_url: URL of the source page.
            **kwargs: Additional parameters (unused).

        Returns:
            JobListExtraction with list of extracted jobs.
        """
        truncated_content = self._truncate_content(content)

        user_prompt = JOB_EXTRACTION_USER_PROMPT.format(
            company=company,
            source_url=source_url,
            content=truncated_content,
        )

        try:
            # Use structured output to get jobs directly
            result = await self.llm.achat_structured(
                message=user_prompt,
                output_schema=JobListExtraction,
                system_prompt=JOB_EXTRACTION_SYSTEM_PROMPT,
            )

            # Ensure source_url is set
            result.source_url = source_url

            # Ensure company name is consistent
            for job in result.jobs:
                if not job.company or job.company == "Unknown":
                    job.company = company

            return result

        except Exception as e:
            # Return empty result on failure
            return JobListExtraction(
                jobs=[],
                source_url=source_url,
                extraction_notes=f"提取失败: {str(e)}",
            )

    async def extract_single(
        self,
        content: str,
        company: str = "Unknown",
        source_url: str = "",
    ) -> Optional[JobPosting]:
        """Extract a single job posting from detail page content.

        Args:
            content: Raw content from job detail page.
            company: Company name.
            source_url: URL of the job detail page.

        Returns:
            Single JobPosting or None if extraction fails.
        """
        result = await self.extract(
            content=content,
            company=company,
            source_url=source_url,
        )

        if result.jobs:
            return result.jobs[0]
        return None
