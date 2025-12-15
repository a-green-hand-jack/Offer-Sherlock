"""Insight extractor for social media content."""

from typing import Optional

from offer_sherlock.crawlers.social_crawler import XhsNote
from offer_sherlock.extractors.base import BaseExtractor
from offer_sherlock.llm.client import LLMClient
from offer_sherlock.schemas.insight import (
    InsightSummary,
    InterviewDifficulty,
    Sentiment,
    SocialPost,
)

# System prompt for social post extraction
POST_EXTRACTION_SYSTEM_PROMPT = """你是一个专业的求职情报分析助手。你的任务是从社交媒体帖子中提取与求职相关的结构化信息。

## 提取规则

1. **内容摘要 (content_summary)**: 用 2-3 句话总结帖子的核心内容
2. **提到的公司 (mentioned_company)**: 帖子中提到的公司名称
3. **提到的职位 (mentioned_position)**: 帖子中提到的岗位/职位
4. **薪资信息 (mentioned_salary)**: 提取薪资相关信息，保持原始表述（如"30k*16"、"年包50w"、"base 25k"等）
5. **情感倾向 (sentiment)**:
   - positive: 推荐、正面评价、表扬公司/团队
   - negative: 避雷、吐槽、负面评价
   - neutral: 客观描述、信息分享
6. **是否面经 (is_interview_experience)**: 是否包含面试经历描述
7. **是否 offer 信息 (is_offer_info)**: 是否包含 offer 或薪资信息

## 注意事项

- 薪资可能有多种表述方式，都要提取
- 区分作者的主观评价和客观信息
- 面经帖通常包含面试流程、题目、难度等描述
- offer 帖通常包含薪资、签约、谈薪等内容"""

# System prompt for insight summarization
INSIGHT_SUMMARY_SYSTEM_PROMPT = """你是一个专业的求职情报分析师。你的任务是综合多条社交媒体帖子，生成一份全面的求职情报汇总。

## 分析维度

1. **薪资估算 (salary_estimate)**: 综合多条帖子的薪资信息，给出一个估算范围
2. **面试难度 (interview_difficulty)**:
   - easy: 面试简单，流程顺利
   - medium: 难度适中，有一定挑战
   - hard: 面试难度大，淘汰率高
   - unknown: 信息不足以判断
3. **综合评价 (overall_sentiment)**:
   - positive: 总体推荐，正面评价居多
   - negative: 总体避雷，负面评价居多
   - neutral: 评价中立或褒贬不一
4. **关键发现 (key_insights)**: 提取 3-5 条最重要的发现
5. **建议 (recommendation)**: 对求职者的简短建议

## 注意事项

- 基于实际帖子内容分析，不要编造信息
- 如果信息不足，明确说明
- 关键发现应该是具体、有价值的信息
- 建议应该实用、可操作"""

INSIGHT_SUMMARY_USER_PROMPT = """请综合分析以下关于 {company} {position_keyword} 的社交媒体帖子，生成情报汇总。

---
帖子列表:
{posts_content}
---

请基于以上 {posts_count} 条帖子，生成一份全面的求职情报汇总。"""


class InsightExtractor(BaseExtractor[InsightSummary]):
    """Extractor for social intelligence from social media posts.

    Analyzes posts from Xiaohongshu and other platforms to extract
    salary information, interview experiences, and sentiment.

    Example:
        >>> extractor = InsightExtractor(llm_client)
        >>> posts = await extractor.extract_posts(xhs_notes)
        >>> summary = await extractor.summarize(posts, "字节跳动", "后端")
        >>> print(summary.to_markdown())
    """

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        max_content_length: int = 20000,
    ):
        """Initialize the insight extractor.

        Args:
            llm_client: LLM client for extraction. Creates default if None.
            max_content_length: Max content length to process.
        """
        if llm_client is None:
            from offer_sherlock.utils.config import LLMProvider

            llm_client = LLMClient(provider=LLMProvider.QWEN, model="qwen-plus")
        super().__init__(llm_client, max_content_length)

    async def extract(
        self,
        content: str,
        company: str = "",
        position_keyword: str = "",
        **kwargs,
    ) -> InsightSummary:
        """Extract insights from raw content (implements base interface).

        For most use cases, use extract_from_notes() or summarize() instead.

        Args:
            content: Raw content to analyze.
            company: Company name for context.
            position_keyword: Position/keyword for context.
            **kwargs: Additional parameters.

        Returns:
            InsightSummary with analysis results.
        """
        # This is a simplified implementation for the base interface
        # For actual use, prefer extract_from_notes() + summarize()
        return InsightSummary(
            company=company or "Unknown",
            position_keyword=position_keyword or "Unknown",
            posts_analyzed=0,
            extraction_notes="Use extract_from_notes() for proper extraction",
        )

    async def extract_from_notes(
        self,
        notes: list[XhsNote],
        batch_size: int = 5,
    ) -> list[SocialPost]:
        """Extract structured data from Xiaohongshu notes.

        Args:
            notes: List of XhsNote objects from crawler.
            batch_size: Number of notes to process in each LLM call.

        Returns:
            List of structured SocialPost objects.
        """
        if not notes:
            return []

        posts = []

        # Process notes in batches for efficiency
        for i in range(0, len(notes), batch_size):
            batch = notes[i : i + batch_size]
            batch_posts = await self._extract_batch(batch)
            posts.extend(batch_posts)

        return posts

    async def _extract_batch(self, notes: list[XhsNote]) -> list[SocialPost]:
        """Extract structured data from a batch of notes.

        Args:
            notes: Batch of XhsNote objects.

        Returns:
            List of extracted SocialPost objects.
        """
        # Format notes for LLM
        notes_content = []
        for i, note in enumerate(notes, 1):
            content = note.content if note.content else "(无内容)"
            notes_content.append(
                f"[帖子 {i}]\n"
                f"标题: {note.title}\n"
                f"作者: {note.user_nickname}\n"
                f"点赞: {note.likes}\n"
                f"内容: {content[:500]}...\n"
                f"链接: {note.url}\n"
            )

        user_prompt = f"""请分析以下 {len(notes)} 条小红书帖子，提取结构化信息。

---
{chr(10).join(notes_content)}
---

对每条帖子，提取：内容摘要、提到的公司、职位、薪资、情感倾向、是否面经、是否offer信息。
返回一个包含所有帖子分析结果的列表。"""

        try:
            # Define a schema for batch extraction
            from pydantic import BaseModel, Field

            class PostBatchExtraction(BaseModel):
                posts: list[SocialPost] = Field(description="提取的帖子列表")

            result = await self.llm.achat_structured(
                message=user_prompt,
                output_schema=PostBatchExtraction,
                system_prompt=POST_EXTRACTION_SYSTEM_PROMPT,
            )

            # Enrich with original note data
            for j, post in enumerate(result.posts):
                if j < len(notes):
                    note = notes[j]
                    post.title = note.title
                    post.author = note.user_nickname
                    post.likes = note.likes
                    post.url = note.url
                    post.source = "xiaohongshu"

            return result.posts

        except Exception as e:
            # On failure, create basic posts from notes
            return [
                SocialPost(
                    title=note.title,
                    content_summary=note.content[:200] if note.content else "无内容",
                    author=note.user_nickname,
                    likes=note.likes,
                    source="xiaohongshu",
                    url=note.url,
                )
                for note in notes
            ]

    async def summarize(
        self,
        posts: list[SocialPost],
        company: str,
        position_keyword: str,
    ) -> InsightSummary:
        """Generate an insight summary from extracted posts.

        Args:
            posts: List of extracted SocialPost objects.
            company: Company name for the summary.
            position_keyword: Position/keyword searched.

        Returns:
            InsightSummary with aggregated analysis.
        """
        if not posts:
            return InsightSummary(
                company=company,
                position_keyword=position_keyword,
                posts_analyzed=0,
                key_insights=["没有找到相关帖子"],
            )

        # Format posts for LLM
        posts_content = []
        for i, post in enumerate(posts, 1):
            sentiment_label = {
                Sentiment.POSITIVE: "正面",
                Sentiment.NEGATIVE: "负面",
                Sentiment.NEUTRAL: "中立",
            }.get(post.sentiment, "中立")

            posts_content.append(
                f"[{i}] {post.title}\n"
                f"    摘要: {post.content_summary}\n"
                f"    情感: {sentiment_label} | 点赞: {post.likes}\n"
                f"    公司: {post.mentioned_company or '未提及'}\n"
                f"    薪资: {post.mentioned_salary or '未提及'}\n"
                f"    面经: {'是' if post.is_interview_experience else '否'} | "
                f"Offer: {'是' if post.is_offer_info else '否'}\n"
            )

        user_prompt = INSIGHT_SUMMARY_USER_PROMPT.format(
            company=company,
            position_keyword=position_keyword,
            posts_content="\n".join(posts_content),
            posts_count=len(posts),
        )

        try:
            # Define schema for summary (without source_posts to avoid circular ref)
            from pydantic import BaseModel, Field

            class SummaryExtraction(BaseModel):
                salary_estimate: Optional[str] = Field(
                    default=None, description="估算薪资范围"
                )
                interview_difficulty: InterviewDifficulty = Field(
                    default=InterviewDifficulty.UNKNOWN, description="面试难度"
                )
                overall_sentiment: Sentiment = Field(
                    default=Sentiment.NEUTRAL, description="综合评价"
                )
                key_insights: list[str] = Field(
                    default_factory=list, description="关键发现"
                )
                recommendation: Optional[str] = Field(
                    default=None, description="建议"
                )

            result = await self.llm.achat_structured(
                message=user_prompt,
                output_schema=SummaryExtraction,
                system_prompt=INSIGHT_SUMMARY_SYSTEM_PROMPT,
            )

            return InsightSummary(
                company=company,
                position_keyword=position_keyword,
                salary_estimate=result.salary_estimate,
                interview_difficulty=result.interview_difficulty,
                overall_sentiment=result.overall_sentiment,
                key_insights=result.key_insights,
                recommendation=result.recommendation,
                source_posts=posts,
                posts_analyzed=len(posts),
            )

        except Exception as e:
            return InsightSummary(
                company=company,
                position_keyword=position_keyword,
                source_posts=posts,
                posts_analyzed=len(posts),
                key_insights=[f"分析失败: {str(e)}"],
            )

    async def analyze_notes(
        self,
        notes: list[XhsNote],
        company: str,
        position_keyword: str,
    ) -> InsightSummary:
        """Convenience method to extract and summarize in one call.

        Args:
            notes: List of XhsNote objects from crawler.
            company: Company name.
            position_keyword: Position/keyword searched.

        Returns:
            InsightSummary with full analysis.
        """
        posts = await self.extract_from_notes(notes)
        return await self.summarize(posts, company, position_keyword)
