"""Tests for InsightExtractor."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from offer_sherlock.extractors.insight_extractor import InsightExtractor
from offer_sherlock.schemas.insight import (
    SocialPost,
    InsightSummary,
    Sentiment,
    InterviewDifficulty,
)
from offer_sherlock.crawlers.social_crawler import XhsNote


class TestInsightExtractor:
    """Tests for InsightExtractor."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        client.achat_structured = AsyncMock()
        return client

    @pytest.fixture
    def extractor(self, mock_llm_client):
        """Create InsightExtractor with mock LLM client."""
        return InsightExtractor(llm_client=mock_llm_client)

    @pytest.fixture
    def sample_notes(self):
        """Create sample XhsNote objects."""
        return [
            XhsNote(
                note_id="note1",
                title="字节跳动后端面经分享",
                content="三轮技术面，主要考察算法和系统设计，难度中等",
                user_nickname="求职小能手",
                likes=500,
                url="https://www.xiaohongshu.com/explore/note1",
            ),
            XhsNote(
                note_id="note2",
                title="拿到字节offer！分享薪资",
                content="base 32k，15薪，签字费8w，股票给了一些",
                user_nickname="offer收割机",
                likes=1200,
                url="https://www.xiaohongshu.com/explore/note2",
            ),
            XhsNote(
                note_id="note3",
                title="字节避雷贴",
                content="加班太严重了，每天10点下班，不推荐",
                user_nickname="离职人员",
                likes=800,
                url="https://www.xiaohongshu.com/explore/note3",
            ),
        ]

    def test_init_default(self):
        """Test default initialization."""
        with patch("offer_sherlock.extractors.insight_extractor.LLMClient") as mock:
            extractor = InsightExtractor()
            mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_from_notes_empty(self, extractor):
        """Test extraction with empty notes list."""
        result = await extractor.extract_from_notes([])
        assert result == []

    @pytest.mark.asyncio
    async def test_extract_from_notes(self, extractor, mock_llm_client, sample_notes):
        """Test extracting structured posts from notes."""
        # Setup mock response
        from pydantic import BaseModel, Field

        class PostBatchExtraction(BaseModel):
            posts: list[SocialPost] = Field(default_factory=list)

        mock_response = PostBatchExtraction(
            posts=[
                SocialPost(
                    title="",  # Will be overwritten
                    content_summary="三轮技术面，考察算法和系统设计",
                    mentioned_company="字节跳动",
                    sentiment=Sentiment.NEUTRAL,
                    is_interview_experience=True,
                ),
                SocialPost(
                    title="",
                    content_summary="薪资 32k*15，签字费8w",
                    mentioned_company="字节跳动",
                    mentioned_salary="32k*15 + 签字费8w",
                    sentiment=Sentiment.POSITIVE,
                    is_offer_info=True,
                ),
                SocialPost(
                    title="",
                    content_summary="加班严重，不推荐",
                    mentioned_company="字节跳动",
                    sentiment=Sentiment.NEGATIVE,
                ),
            ]
        )
        mock_llm_client.achat_structured.return_value = mock_response

        result = await extractor.extract_from_notes(sample_notes)

        assert len(result) == 3
        # Original note data should be preserved
        assert result[0].title == "字节跳动后端面经分享"
        assert result[0].author == "求职小能手"
        assert result[0].likes == 500
        assert result[0].source == "xiaohongshu"

    @pytest.mark.asyncio
    async def test_extract_from_notes_handles_error(
        self, extractor, mock_llm_client, sample_notes
    ):
        """Test graceful error handling during extraction."""
        mock_llm_client.achat_structured.side_effect = Exception("API Error")

        result = await extractor.extract_from_notes(sample_notes)

        # Should return basic posts created from notes
        assert len(result) == 3
        assert result[0].title == "字节跳动后端面经分享"

    @pytest.mark.asyncio
    async def test_summarize_empty_posts(self, extractor):
        """Test summarization with empty posts list."""
        result = await extractor.summarize([], "字节跳动", "后端")

        assert result.company == "字节跳动"
        assert result.posts_analyzed == 0
        assert "没有找到相关帖子" in result.key_insights

    @pytest.mark.asyncio
    async def test_summarize(self, extractor, mock_llm_client):
        """Test generating insight summary from posts."""
        posts = [
            SocialPost(
                title="面经",
                content_summary="面试不难",
                sentiment=Sentiment.POSITIVE,
                likes=100,
            ),
            SocialPost(
                title="Offer",
                content_summary="薪资不错",
                mentioned_salary="30k*16",
                sentiment=Sentiment.POSITIVE,
                likes=200,
            ),
        ]

        # Setup mock response
        from pydantic import BaseModel, Field
        from typing import Optional

        class SummaryExtraction(BaseModel):
            salary_estimate: Optional[str] = None
            interview_difficulty: InterviewDifficulty = InterviewDifficulty.UNKNOWN
            overall_sentiment: Sentiment = Sentiment.NEUTRAL
            key_insights: list[str] = Field(default_factory=list)
            recommendation: Optional[str] = None

        mock_response = SummaryExtraction(
            salary_estimate="28k-35k * 16薪",
            interview_difficulty=InterviewDifficulty.MEDIUM,
            overall_sentiment=Sentiment.POSITIVE,
            key_insights=[
                "面试难度适中",
                "薪资竞争力强",
                "工作氛围好",
            ],
            recommendation="推荐投递",
        )
        mock_llm_client.achat_structured.return_value = mock_response

        result = await extractor.summarize(posts, "腾讯", "后端")

        assert result.company == "腾讯"
        assert result.position_keyword == "后端"
        assert result.salary_estimate == "28k-35k * 16薪"
        assert result.interview_difficulty == InterviewDifficulty.MEDIUM
        assert result.overall_sentiment == Sentiment.POSITIVE
        assert len(result.key_insights) == 3
        assert result.posts_analyzed == 2
        assert len(result.source_posts) == 2

    @pytest.mark.asyncio
    async def test_summarize_handles_error(self, extractor, mock_llm_client):
        """Test graceful error handling during summarization."""
        posts = [
            SocialPost(title="Test", content_summary="Test content", likes=10)
        ]
        mock_llm_client.achat_structured.side_effect = Exception("API Error")

        result = await extractor.summarize(posts, "TestCorp", "测试")

        assert result.company == "TestCorp"
        assert result.posts_analyzed == 1
        assert "分析失败" in result.key_insights[0]

    @pytest.mark.asyncio
    async def test_analyze_notes(self, extractor, mock_llm_client, sample_notes):
        """Test the convenience method that combines extraction and summarization."""
        # First call for extract_from_notes
        from pydantic import BaseModel, Field

        class PostBatchExtraction(BaseModel):
            posts: list[SocialPost] = Field(default_factory=list)

        mock_posts = PostBatchExtraction(
            posts=[
                SocialPost(
                    title="",
                    content_summary="Test summary",
                    sentiment=Sentiment.POSITIVE,
                )
                for _ in sample_notes
            ]
        )

        # Second call for summarize
        from typing import Optional

        class SummaryExtraction(BaseModel):
            salary_estimate: Optional[str] = None
            interview_difficulty: InterviewDifficulty = InterviewDifficulty.UNKNOWN
            overall_sentiment: Sentiment = Sentiment.NEUTRAL
            key_insights: list[str] = Field(default_factory=list)
            recommendation: Optional[str] = None

        mock_summary = SummaryExtraction(
            overall_sentiment=Sentiment.POSITIVE,
            key_insights=["Good company"],
        )

        mock_llm_client.achat_structured.side_effect = [mock_posts, mock_summary]

        result = await extractor.analyze_notes(sample_notes, "字节跳动", "后端")

        assert result.company == "字节跳动"
        assert result.position_keyword == "后端"
        assert mock_llm_client.achat_structured.call_count == 2
