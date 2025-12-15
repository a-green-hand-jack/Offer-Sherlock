"""Social intelligence schemas for interview experiences and offer info."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Sentiment(str, Enum):
    """Sentiment classification for social posts."""

    POSITIVE = "positive"  # 推荐、正面评价
    NEGATIVE = "negative"  # 避雷、负面评价
    NEUTRAL = "neutral"  # 中立、客观描述


class InterviewDifficulty(str, Enum):
    """Interview difficulty levels."""

    EASY = "easy"  # 简单
    MEDIUM = "medium"  # 中等
    HARD = "hard"  # 困难
    UNKNOWN = "unknown"  # 未知


class SocialPost(BaseModel):
    """Structured data extracted from a social media post.

    Represents interview experiences, offer information, or company reviews
    from platforms like Xiaohongshu, Zhihu, etc.

    Attributes:
        title: Post title.
        content_summary: LLM-generated summary of the post content.
        author: Author nickname.
        likes: Number of likes/upvotes.
        source: Platform name (xiaohongshu, zhihu, etc.).
        url: Link to the original post.
        mentioned_company: Company mentioned in the post.
        mentioned_position: Position/role mentioned.
        mentioned_salary: Salary information if mentioned.
        sentiment: Overall sentiment of the post.
        is_interview_experience: Whether this is an interview experience post.
        is_offer_info: Whether this contains offer/salary information.
    """

    title: str = Field(description="帖子标题")
    content_summary: str = Field(description="内容摘要（由 LLM 提取的关键信息）")
    author: str = Field(default="", description="作者昵称")
    likes: int = Field(default=0, description="点赞数")
    source: str = Field(default="xiaohongshu", description="来源平台")
    url: str = Field(default="", description="原帖链接")

    mentioned_company: Optional[str] = Field(
        default=None, description="提到的公司名称"
    )
    mentioned_position: Optional[str] = Field(
        default=None, description="提到的岗位/职位"
    )
    mentioned_salary: Optional[str] = Field(
        default=None, description="提到的薪资信息（如 30k*16, 年包50w 等）"
    )
    sentiment: Sentiment = Field(
        default=Sentiment.NEUTRAL, description="情感倾向"
    )
    is_interview_experience: bool = Field(
        default=False, description="是否为面经帖"
    )
    is_offer_info: bool = Field(
        default=False, description="是否包含 offer/薪资信息"
    )

    def __str__(self) -> str:
        emoji = {"positive": "+", "negative": "-", "neutral": "o"}[self.sentiment.value]
        return f"[{emoji}] {self.title[:40]}... ({self.likes} likes)"


class InsightSummary(BaseModel):
    """Aggregated intelligence summary for a company/position.

    Combines multiple social posts to provide an overall assessment
    of salary expectations, interview difficulty, and sentiment.

    Attributes:
        company: Company name being analyzed.
        position_keyword: Search keyword used to find posts.
        salary_estimate: Estimated salary range based on posts.
        interview_difficulty: Overall interview difficulty assessment.
        overall_sentiment: Aggregated sentiment across posts.
        key_insights: Key findings extracted from posts (3-5 bullet points).
        recommendation: Brief recommendation for job seekers.
        source_posts: List of posts used to generate this summary.
        posts_analyzed: Number of posts analyzed.
    """

    company: str = Field(description="分析的公司名称")
    position_keyword: str = Field(description="搜索使用的关键词")
    salary_estimate: Optional[str] = Field(
        default=None, description="估算薪资范围（综合多条帖子）"
    )
    interview_difficulty: InterviewDifficulty = Field(
        default=InterviewDifficulty.UNKNOWN, description="面试难度评估"
    )
    overall_sentiment: Sentiment = Field(
        default=Sentiment.NEUTRAL, description="综合情感倾向"
    )
    key_insights: list[str] = Field(
        default_factory=list, description="关键发现（3-5 条）"
    )
    recommendation: Optional[str] = Field(
        default=None, description="对求职者的简要建议"
    )
    source_posts: list[SocialPost] = Field(
        default_factory=list, description="来源帖子列表"
    )
    posts_analyzed: int = Field(default=0, description="分析的帖子总数")

    def __str__(self) -> str:
        sentiment_emoji = {
            "positive": "recommend",
            "negative": "avoid",
            "neutral": "neutral",
        }[self.overall_sentiment.value]
        return (
            f"InsightSummary({self.company} - {self.position_keyword}): "
            f"{sentiment_emoji}, {self.posts_analyzed} posts"
        )

    def to_markdown(self) -> str:
        """Generate a markdown report of the insights."""
        lines = [
            f"# {self.company} - {self.position_keyword} 情报汇总",
            "",
            f"**综合评价**: {self.overall_sentiment.value}",
            f"**面试难度**: {self.interview_difficulty.value}",
        ]

        if self.salary_estimate:
            lines.append(f"**薪资估算**: {self.salary_estimate}")

        lines.append("")
        lines.append("## 关键发现")
        for insight in self.key_insights:
            lines.append(f"- {insight}")

        if self.recommendation:
            lines.append("")
            lines.append(f"## 建议")
            lines.append(self.recommendation)

        lines.append("")
        lines.append(f"---")
        lines.append(f"*基于 {self.posts_analyzed} 条社交媒体帖子分析*")

        return "\n".join(lines)
