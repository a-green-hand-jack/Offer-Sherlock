"""Tests for insight schemas."""

import pytest
from offer_sherlock.schemas.insight import (
    SocialPost,
    InsightSummary,
    Sentiment,
    InterviewDifficulty,
)


class TestSocialPost:
    """Tests for SocialPost schema."""

    def test_create_minimal(self):
        """Test creating SocialPost with minimal fields."""
        post = SocialPost(
            title="字节跳动后端面经",
            content_summary="三轮技术面，问了很多算法题",
        )
        assert post.title == "字节跳动后端面经"
        assert post.sentiment == Sentiment.NEUTRAL
        assert post.is_interview_experience is False

    def test_create_full(self):
        """Test creating SocialPost with all fields."""
        post = SocialPost(
            title="收到字节offer啦！分享薪资",
            content_summary="base 30k，签字费5w，股票若干",
            author="求职小能手",
            likes=1234,
            source="xiaohongshu",
            url="https://www.xiaohongshu.com/explore/abc123",
            mentioned_company="字节跳动",
            mentioned_position="后端开发",
            mentioned_salary="30k*15 + 签字费5w",
            sentiment=Sentiment.POSITIVE,
            is_interview_experience=False,
            is_offer_info=True,
        )
        assert post.mentioned_salary == "30k*15 + 签字费5w"
        assert post.sentiment == Sentiment.POSITIVE
        assert post.is_offer_info is True

    def test_str_representation(self):
        """Test string representation with different sentiments."""
        positive_post = SocialPost(
            title="强烈推荐这家公司",
            content_summary="团队氛围好",
            likes=100,
            sentiment=Sentiment.POSITIVE,
        )
        assert "[+]" in str(positive_post)

        negative_post = SocialPost(
            title="避雷！千万别来",
            content_summary="加班严重",
            likes=500,
            sentiment=Sentiment.NEGATIVE,
        )
        assert "[-]" in str(negative_post)

        neutral_post = SocialPost(
            title="面试流程分享",
            content_summary="三轮面试",
            sentiment=Sentiment.NEUTRAL,
        )
        assert "[o]" in str(neutral_post)


class TestInsightSummary:
    """Tests for InsightSummary schema."""

    def test_create_minimal(self):
        """Test creating InsightSummary with minimal fields."""
        summary = InsightSummary(
            company="腾讯",
            position_keyword="后端 校招",
        )
        assert summary.company == "腾讯"
        assert summary.posts_analyzed == 0
        assert summary.interview_difficulty == InterviewDifficulty.UNKNOWN

    def test_create_full(self):
        """Test creating InsightSummary with all fields."""
        posts = [
            SocialPost(
                title="腾讯面经",
                content_summary="面试体验不错",
                sentiment=Sentiment.POSITIVE,
            ),
            SocialPost(
                title="腾讯offer",
                content_summary="薪资还可以",
                mentioned_salary="28k*16",
                sentiment=Sentiment.POSITIVE,
            ),
        ]

        summary = InsightSummary(
            company="腾讯",
            position_keyword="后端 校招",
            salary_estimate="25k-35k * 16薪",
            interview_difficulty=InterviewDifficulty.MEDIUM,
            overall_sentiment=Sentiment.POSITIVE,
            key_insights=[
                "面试难度适中，主要考察基础",
                "薪资在大厂中处于中等水平",
                "工作生活平衡较好",
            ],
            recommendation="推荐投递，准备好八股文和算法",
            source_posts=posts,
            posts_analyzed=2,
        )
        assert summary.salary_estimate == "25k-35k * 16薪"
        assert len(summary.key_insights) == 3
        assert summary.posts_analyzed == 2

    def test_str_representation(self):
        """Test string representation."""
        summary = InsightSummary(
            company="阿里巴巴",
            position_keyword="Java",
            overall_sentiment=Sentiment.NEGATIVE,
            posts_analyzed=10,
        )
        s = str(summary)
        assert "阿里巴巴" in s
        assert "Java" in s
        assert "10 posts" in s

    def test_to_markdown(self):
        """Test markdown generation."""
        summary = InsightSummary(
            company="美团",
            position_keyword="算法",
            salary_estimate="30k-40k",
            interview_difficulty=InterviewDifficulty.HARD,
            overall_sentiment=Sentiment.NEUTRAL,
            key_insights=[
                "面试难度较大",
                "算法题很多",
            ],
            recommendation="建议充分准备",
            posts_analyzed=5,
        )
        md = summary.to_markdown()
        assert "# 美团 - 算法 情报汇总" in md
        assert "30k-40k" in md
        assert "hard" in md
        assert "面试难度较大" in md
        assert "建议充分准备" in md
        assert "5 条社交媒体帖子" in md

    def test_json_serialization(self):
        """Test JSON serialization."""
        summary = InsightSummary(
            company="字节跳动",
            position_keyword="前端",
            overall_sentiment=Sentiment.POSITIVE,
            key_insights=["薪资高", "成长快"],
            posts_analyzed=3,
        )
        json_str = summary.model_dump_json()
        assert "字节跳动" in json_str
        assert "positive" in json_str

        # Deserialize
        loaded = InsightSummary.model_validate_json(json_str)
        assert loaded.company == "字节跳动"
        assert loaded.overall_sentiment == Sentiment.POSITIVE


class TestSentimentEnum:
    """Tests for Sentiment enum."""

    def test_enum_values(self):
        """Test enum values."""
        assert Sentiment.POSITIVE.value == "positive"
        assert Sentiment.NEGATIVE.value == "negative"
        assert Sentiment.NEUTRAL.value == "neutral"

    def test_enum_from_string(self):
        """Test creating enum from string."""
        assert Sentiment("positive") == Sentiment.POSITIVE
        assert Sentiment("negative") == Sentiment.NEGATIVE


class TestInterviewDifficultyEnum:
    """Tests for InterviewDifficulty enum."""

    def test_enum_values(self):
        """Test enum values."""
        assert InterviewDifficulty.EASY.value == "easy"
        assert InterviewDifficulty.MEDIUM.value == "medium"
        assert InterviewDifficulty.HARD.value == "hard"
        assert InterviewDifficulty.UNKNOWN.value == "unknown"
