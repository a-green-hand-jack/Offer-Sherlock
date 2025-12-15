"""Tests for JobExtractor."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from offer_sherlock.extractors.job_extractor import JobExtractor
from offer_sherlock.schemas.job import JobPosting, JobListExtraction


# Sample content for testing
SAMPLE_JOB_LIST_CONTENT = """
# 字节跳动校园招聘

## 搜索结果

### [后端开发工程师](https://jobs.bytedance.com/job/123456)
- 工作地点: 北京
- 岗位类型: 校招
- 要求: 熟悉 Go/Python，了解分布式系统

### [前端开发工程师](https://jobs.bytedance.com/job/123457)
- 工作地点: 上海
- 岗位类型: 校招
- 要求: 熟悉 React/Vue，了解前端工程化

### [算法工程师](https://jobs.bytedance.com/job/123458)
- 工作地点: 北京/深圳
- 岗位类型: 校招
- 薪资: 35k-50k
- 要求: 熟悉机器学习算法，有相关论文发表优先
"""

SAMPLE_JOB_DETAIL_CONTENT = """
# 后端开发工程师 - 字节跳动

岗位 ID: JOB-2024-123456

## 岗位描述

负责抖音后端服务开发，包括：
- 高并发系统设计与实现
- 服务性能优化
- 技术方案设计

## 岗位要求

- 本科及以上学历，计算机相关专业
- 熟悉 Go/Python/Java 至少一门语言
- 了解 MySQL、Redis、Kafka 等中间件
- 有大规模系统开发经验优先

## 工作地点

北京市海淀区

## 投递链接

[立即投递](https://jobs.bytedance.com/apply/123456)
"""


class TestJobExtractor:
    """Tests for JobExtractor."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        client.achat_structured = AsyncMock()
        return client

    @pytest.fixture
    def extractor(self, mock_llm_client):
        """Create a JobExtractor with mock LLM client."""
        return JobExtractor(llm_client=mock_llm_client)

    def test_init_default(self):
        """Test default initialization creates LLM client."""
        with patch("offer_sherlock.extractors.job_extractor.LLMClient") as mock:
            extractor = JobExtractor()
            # Should create a qwen-plus client
            mock.assert_called_once()

    def test_truncate_content(self, extractor):
        """Test content truncation."""
        short_content = "Short content"
        assert extractor._truncate_content(short_content) == short_content

        long_content = "x" * 20000
        truncated = extractor._truncate_content(long_content)
        assert len(truncated) < 20000
        assert "[... 内容已截断 ...]" in truncated

    @pytest.mark.asyncio
    async def test_extract_job_list(self, extractor, mock_llm_client):
        """Test extracting multiple jobs from list page."""
        # Setup mock response
        mock_response = JobListExtraction(
            jobs=[
                JobPosting(
                    title="后端开发工程师",
                    company="字节跳动",
                    job_id_external="123456",
                    location="北京",
                    job_type="校招",
                ),
                JobPosting(
                    title="前端开发工程师",
                    company="字节跳动",
                    job_id_external="123457",
                    location="上海",
                    job_type="校招",
                ),
            ],
            source_url="",
        )
        mock_llm_client.achat_structured.return_value = mock_response

        # Execute
        result = await extractor.extract(
            content=SAMPLE_JOB_LIST_CONTENT,
            company="字节跳动",
            source_url="https://jobs.bytedance.com",
        )

        # Verify
        assert result.count == 2
        assert result.source_url == "https://jobs.bytedance.com"
        assert result.jobs[0].title == "后端开发工程师"
        assert result.jobs[0].company == "字节跳动"

    @pytest.mark.asyncio
    async def test_extract_single_job(self, extractor, mock_llm_client):
        """Test extracting single job from detail page."""
        mock_response = JobListExtraction(
            jobs=[
                JobPosting(
                    title="后端开发工程师",
                    company="字节跳动",
                    job_id_external="JOB-2024-123456",
                    location="北京市海淀区",
                    job_type="校招",
                    requirements="熟悉 Go/Python/Java，了解中间件",
                    apply_link="https://jobs.bytedance.com/apply/123456",
                ),
            ],
            source_url="",
        )
        mock_llm_client.achat_structured.return_value = mock_response

        result = await extractor.extract_single(
            content=SAMPLE_JOB_DETAIL_CONTENT,
            company="字节跳动",
            source_url="https://jobs.bytedance.com/job/123456",
        )

        assert result is not None
        assert result.title == "后端开发工程师"
        assert result.job_id_external == "JOB-2024-123456"
        assert result.apply_link is not None

    @pytest.mark.asyncio
    async def test_extract_handles_error(self, extractor, mock_llm_client):
        """Test extraction handles LLM errors gracefully."""
        mock_llm_client.achat_structured.side_effect = Exception("LLM API Error")

        result = await extractor.extract(
            content="Some content",
            company="TestCorp",
            source_url="https://example.com",
        )

        assert result.count == 0
        assert "提取失败" in result.extraction_notes
        assert "LLM API Error" in result.extraction_notes

    @pytest.mark.asyncio
    async def test_extract_fills_missing_company(self, extractor, mock_llm_client):
        """Test that missing company names are filled in."""
        mock_response = JobListExtraction(
            jobs=[
                JobPosting(title="工程师", company="Unknown"),
                JobPosting(title="设计师", company=""),
            ],
            source_url="",
        )
        mock_llm_client.achat_structured.return_value = mock_response

        result = await extractor.extract(
            content="Content",
            company="华为",
            source_url="https://career.huawei.com",
        )

        # All jobs should have company set to "华为"
        for job in result.jobs:
            assert job.company == "华为"

    @pytest.mark.asyncio
    async def test_extract_single_returns_none_on_empty(
        self, extractor, mock_llm_client
    ):
        """Test extract_single returns None when no jobs found."""
        mock_response = JobListExtraction(jobs=[], source_url="")
        mock_llm_client.achat_structured.return_value = mock_response

        result = await extractor.extract_single(
            content="Empty page",
            company="TestCorp",
        )

        assert result is None
