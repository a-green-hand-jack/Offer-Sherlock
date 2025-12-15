#!/usr/bin/env python3
"""测试小红书爬虫模块。"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from offer_sherlock.crawlers import XhsCrawler


async def test_search():
    """测试搜索功能。"""
    print("=" * 60)
    print("🧪 测试小红书爬虫 - 搜索功能")
    print("=" * 60)

    async with XhsCrawler(headless=False) as crawler:
        # 测试搜索
        keyword = "字节跳动 面经"
        print(f"\n🔍 搜索: {keyword}")

        notes = await crawler.search(keyword, max_results=10)

        if notes:
            print(f"\n✅ 找到 {len(notes)} 条笔记:\n")
            for i, note in enumerate(notes, 1):
                print(f"[{i}] {note.title[:50]}")
                print(f"    作者: {note.user_nickname}")
                print(f"    点赞: {note.likes}")
                print(f"    ID: {note.note_id}")
                print()

            # 测试获取第一条笔记的详情
            if notes:
                print("-" * 60)
                print("📖 获取第一条笔记详情...")
                detail = await crawler.get_note_detail(notes[0].note_id)
                if detail:
                    print(f"\n标题: {detail.title}")
                    print(f"作者: {detail.user_nickname}")
                    print(f"点赞: {detail.likes} | 收藏: {detail.collects} | 评论: {detail.comments}")
                    if detail.tags:
                        print(f"标签: {', '.join(detail.tags)}")
                    if detail.content:
                        print(f"\n内容预览:\n{detail.content[:300]}...")
        else:
            print("❌ 未找到搜索结果")


async def test_crawl_interface():
    """测试 BaseCrawler 接口。"""
    print("\n" + "=" * 60)
    print("🧪 测试 BaseCrawler 接口")
    print("=" * 60)

    async with XhsCrawler(headless=False) as crawler:
        # 使用关键词作为 URL
        result = await crawler.crawl("腾讯 校招 offer", max_results=5)

        print(f"\n成功: {result.success}")
        print(f"笔记数: {result.metadata.get('notes_count', 0)}")
        print(f"\nMarkdown 预览:\n{result.markdown[:500]}...")


async def main():
    await test_search()
    # await test_crawl_interface()


if __name__ == "__main__":
    asyncio.run(main())
