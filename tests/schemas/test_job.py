"""Tests for job schemas."""

import pytest
from offer_sherlock.schemas.job import JobPosting, JobListExtraction


class TestJobPosting:
    """Tests for JobPosting schema."""

    def test_create_minimal(self):
        """Test creating JobPosting with minimal required fields."""
        job = JobPosting(title="后端开发工程师", company="字节跳动")
        assert job.title == "后端开发工程师"
        assert job.company == "字节跳动"
        assert job.job_id_external is None
        assert job.location is None

    def test_create_full(self):
        """Test creating JobPosting with all fields."""
        job = JobPosting(
            title="后端开发工程师",
            company="字节跳动",
            job_id_external="JOB123456",
            location="北京",
            job_type="校招",
            requirements="熟悉 Python/Go，了解分布式系统",
            salary_range="25k-45k * 15薪",
            apply_link="https://jobs.bytedance.com/job/123456",
        )
        assert job.job_id_external == "JOB123456"
        assert job.location == "北京"
        assert job.job_type == "校招"
        assert job.salary_range == "25k-45k * 15薪"

    def test_str_representation(self):
        """Test string representation of JobPosting."""
        job = JobPosting(
            title="后端开发",
            company="腾讯",
            location="深圳",
            job_type="校招",
            salary_range="30k*16",
        )
        s = str(job)
        assert "后端开发" in s
        assert "腾讯" in s
        assert "深圳" in s
        assert "校招" in s
        assert "30k*16" in s

    def test_str_minimal(self):
        """Test string representation with minimal fields."""
        job = JobPosting(title="SRE", company="Google")
        s = str(job)
        assert "SRE" in s
        assert "Google" in s


class TestJobListExtraction:
    """Tests for JobListExtraction schema."""

    def test_create_empty(self):
        """Test creating empty JobListExtraction."""
        extraction = JobListExtraction(source_url="https://example.com/jobs")
        assert extraction.jobs == []
        assert extraction.count == 0
        assert extraction.source_url == "https://example.com/jobs"

    def test_create_with_jobs(self):
        """Test creating JobListExtraction with jobs."""
        jobs = [
            JobPosting(title="前端开发", company="阿里巴巴"),
            JobPosting(title="后端开发", company="阿里巴巴"),
            JobPosting(title="算法工程师", company="阿里巴巴"),
        ]
        extraction = JobListExtraction(
            jobs=jobs,
            source_url="https://talent.alibaba.com",
            extraction_notes="提取了3个校招岗位",
        )
        assert extraction.count == 3
        assert extraction.extraction_notes == "提取了3个校招岗位"

    def test_str_representation(self):
        """Test string representation of JobListExtraction."""
        extraction = JobListExtraction(
            jobs=[JobPosting(title="Test", company="Test")],
            source_url="https://example.com",
        )
        s = str(extraction)
        assert "1 jobs" in s
        assert "example.com" in s

    def test_json_serialization(self):
        """Test JSON serialization."""
        job = JobPosting(
            title="测试工程师",
            company="美团",
            location="北京",
        )
        extraction = JobListExtraction(
            jobs=[job],
            source_url="https://zhaopin.meituan.com",
        )
        json_str = extraction.model_dump_json()
        assert "测试工程师" in json_str
        assert "美团" in json_str

        # Deserialize and verify
        loaded = JobListExtraction.model_validate_json(json_str)
        assert loaded.count == 1
        assert loaded.jobs[0].title == "测试工程师"
