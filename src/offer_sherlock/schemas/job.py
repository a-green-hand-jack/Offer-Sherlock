"""Job posting schemas for official recruitment sites."""

from typing import Optional

from pydantic import BaseModel, Field


class JobPosting(BaseModel):
    """Structured job posting extracted from official recruitment sites.

    Attributes:
        title: Job title/position name.
        company: Company name.
        job_id_external: External ID from the source site (for deduplication).
        location: Work location(s).
        job_type: Type of position (campus/social/intern).
        requirements: Key requirements summarized by LLM.
        salary_range: Salary range if available.
        apply_link: Link to apply for the position.
    """

    title: str = Field(description="岗位名称")
    company: str = Field(description="公司名称")
    job_id_external: Optional[str] = Field(
        default=None, description="外部岗位 ID（用于去重，通常在 URL 或页面中）"
    )
    location: Optional[str] = Field(default=None, description="工作地点")
    job_type: Optional[str] = Field(
        default=None, description="岗位类型：校招/社招/实习"
    )
    requirements: Optional[str] = Field(
        default=None, description="核心要求（简要总结）"
    )
    salary_range: Optional[str] = Field(
        default=None, description="薪资范围（如页面中有显示）"
    )
    apply_link: Optional[str] = Field(default=None, description="投递/申请链接")

    def __str__(self) -> str:
        parts = [f"{self.title} @ {self.company}"]
        if self.location:
            parts.append(f"[{self.location}]")
        if self.job_type:
            parts.append(f"({self.job_type})")
        if self.salary_range:
            parts.append(f"- {self.salary_range}")
        return " ".join(parts)


class JobListExtraction(BaseModel):
    """Result of extracting multiple jobs from a single page.

    Attributes:
        jobs: List of extracted job postings.
        source_url: The URL where jobs were extracted from.
        extraction_notes: Additional notes from the LLM about the extraction.
    """

    jobs: list[JobPosting] = Field(
        default_factory=list, description="提取到的岗位列表"
    )
    source_url: str = Field(description="来源页面 URL")
    extraction_notes: Optional[str] = Field(
        default=None,
        description="提取过程中的补充说明（如页面结构特殊、部分信息缺失等）",
    )

    @property
    def count(self) -> int:
        """Number of jobs extracted."""
        return len(self.jobs)

    def __str__(self) -> str:
        return f"JobListExtraction({self.count} jobs from {self.source_url})"
