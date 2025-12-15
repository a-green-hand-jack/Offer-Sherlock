"""
小红书社交情报爬虫模块。

使用 Playwright 浏览器直接访问小红书，绕过复杂的签名机制。
需要用户手动登录一次，之后可以自动搜索和提取笔记内容。
"""

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from .base import BaseCrawler, CrawlResult


@dataclass
class XhsNote:
    """小红书笔记数据。"""

    note_id: str
    title: str
    content: str = ""
    user_nickname: str = ""
    user_id: str = ""
    likes: int = 0
    comments: int = 0
    collects: int = 0
    publish_time: str = ""
    note_type: str = ""  # normal, video
    tags: list[str] = field(default_factory=list)
    url: str = ""

    def to_dict(self) -> dict:
        """转换为字典。"""
        return {
            "note_id": self.note_id,
            "title": self.title,
            "content": self.content,
            "user_nickname": self.user_nickname,
            "user_id": self.user_id,
            "likes": self.likes,
            "comments": self.comments,
            "collects": self.collects,
            "publish_time": self.publish_time,
            "note_type": self.note_type,
            "tags": self.tags,
            "url": self.url,
        }


class XhsCrawler(BaseCrawler):
    """
    小红书爬虫。

    使用 Playwright 浏览器进行搜索和内容提取。
    首次使用需要手动登录，之后会保存会话状态。

    Usage:
        crawler = XhsCrawler()
        notes = await crawler.search("字节跳动 面经", max_results=10)
        for note in notes:
            print(note.title, note.likes)
    """

    def __init__(
        self,
        headless: bool = False,
        storage_state_path: Optional[str] = None,
        timeout: int = 30000,
    ):
        """
        初始化小红书爬虫。

        Args:
            headless: 是否使用无头模式（首次登录建议 False）
            storage_state_path: 浏览器状态保存路径（用于保持登录）
            timeout: 页面加载超时时间（毫秒）
        """
        self.headless = headless
        self.storage_state_path = storage_state_path or str(
            Path(__file__).parent.parent.parent.parent / "data" / "xhs_browser_state.json"
        )
        self.timeout = timeout

        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._playwright = None

    async def _ensure_browser(self) -> Page:
        """确保浏览器已启动并返回页面。"""
        if self._page is not None:
            return self._page

        self._playwright = await async_playwright().start()

        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )

        # 尝试加载已保存的状态
        storage_path = Path(self.storage_state_path)
        if storage_path.exists():
            try:
                self._context = await self._browser.new_context(
                    storage_state=str(storage_path),
                    viewport={"width": 1280, "height": 800},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                )
            except Exception:
                self._context = None

        if self._context is None:
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            )

        self._page = await self._context.new_page()
        return self._page

    async def _ensure_logged_in(self, page: Page, max_wait: int = 180) -> bool:
        """
        确保已登录小红书。

        如果已有保存的登录状态，会先尝试使用。
        如果未登录，会等待用户手动登录。

        Args:
            page: Playwright 页面对象
            max_wait: 最大等待时间（秒）

        Returns:
            是否登录成功
        """
        # 先检查是否已有 cookie（从保存的状态加载的）
        cookies = await self._context.cookies()
        cookie_names = [c["name"] for c in cookies]

        if "web_session" in cookie_names:
            print("✅ 使用已保存的登录状态")
            return True

        # 没有登录状态，访问首页让用户登录
        await page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded")
        await asyncio.sleep(2)

        # 再次检查（访问首页后可能会触发 cookie 设置）
        cookies = await self._context.cookies()
        cookie_names = [c["name"] for c in cookies]

        if "web_session" in cookie_names:
            await self._save_state()
            return True

        # 等待用户登录
        print("⏳ 请在浏览器中登录小红书（最长等待 %d 秒）..." % max_wait)
        waited = 0
        while waited < max_wait:
            cookies = await self._context.cookies()
            cookie_names = [c["name"] for c in cookies]
            if "web_session" in cookie_names:
                # 保存状态
                await self._save_state()
                print("✅ 登录成功，状态已保存")
                return True
            await asyncio.sleep(2)
            waited += 2
            if waited % 30 == 0:
                print(f"   等待中... ({waited}秒)")

        return False

    async def _save_state(self):
        """保存浏览器状态（cookie 等）。"""
        if self._context:
            storage_path = Path(self.storage_state_path)
            storage_path.parent.mkdir(parents=True, exist_ok=True)
            await self._context.storage_state(path=str(storage_path))

    async def _handle_login_modal(self, page: Page, max_wait: int = 120) -> bool:
        """处理搜索页面的登录弹窗。"""
        login_modal = await page.query_selector('text="登录后查看搜索结果"')
        if not login_modal:
            return True

        print("⚠️ 需要登录才能查看搜索结果，请在浏览器中登录...")

        waited = 0
        while waited < max_wait:
            login_modal = await page.query_selector('text="登录后查看搜索结果"')
            if not login_modal:
                await self._save_state()
                return True
            await asyncio.sleep(2)
            waited += 2

        return False

    async def search(
        self,
        keyword: str,
        max_results: int = 20,
        sort_by: str = "general",  # general, time_descending, popularity_descending
    ) -> list[XhsNote]:
        """
        搜索小红书笔记。

        Args:
            keyword: 搜索关键词
            max_results: 最大返回数量
            sort_by: 排序方式

        Returns:
            笔记列表
        """
        page = await self._ensure_browser()

        # 确保已登录
        if not await self._ensure_logged_in(page):
            print("❌ 登录失败")
            return []

        # 构建搜索 URL
        encoded_keyword = quote(keyword)
        search_url = f"https://www.xiaohongshu.com/search_result?keyword={encoded_keyword}&source=web_search_result_notes"

        await page.goto(search_url, wait_until="domcontentloaded", timeout=self.timeout)
        await asyncio.sleep(3)

        # 处理登录弹窗
        if not await self._handle_login_modal(page):
            print("❌ 登录超时")
            return []

        await asyncio.sleep(2)

        # 滚动加载更多
        await page.evaluate("window.scrollTo(0, 500)")
        await asyncio.sleep(2)

        # 提取搜索结果
        notes = await self._extract_search_results(page, max_results)

        return notes

    async def _extract_search_results(self, page: Page, max_results: int) -> list[XhsNote]:
        """从搜索页面提取结果。"""
        notes = []

        # 从 DOM 提取
        try:
            note_elements = await page.query_selector_all(
                'section.note-item, div[data-v-a264b01a].note-item, .feeds-page section'
            )

            for elem in note_elements[:max_results]:
                try:
                    note = await self._parse_note_element(elem)
                    if note:
                        notes.append(note)
                except Exception:
                    continue

        except Exception as e:
            print(f"DOM 提取失败: {e}")

        # 如果 DOM 提取失败，尝试从 API 响应提取
        if not notes:
            notes = await self._extract_from_api(page, max_results)

        return notes

    async def _parse_note_element(self, elem) -> Optional[XhsNote]:
        """解析单个笔记元素。"""
        # 获取链接和 ID
        link_el = await elem.query_selector('a[href*="/explore/"], a[href*="/search_result/"]')
        href = await link_el.get_attribute("href") if link_el else ""

        note_id = ""
        if href:
            match = re.search(r'/explore/([a-f0-9]+)', href)
            if match:
                note_id = match.group(1)

        if not note_id:
            return None

        # 获取标题
        title_el = await elem.query_selector('.title span, .note-content .title, a.title, .title')
        title = await title_el.inner_text() if title_el else "无标题"

        # 获取作者
        author_el = await elem.query_selector('.author-wrapper .name, .user-info .name, .author .name')
        author = await author_el.inner_text() if author_el else ""

        # 获取点赞数
        likes = 0
        likes_el = await elem.query_selector('.like-wrapper .count, .engage-bar .like .count')
        if likes_el:
            likes_text = await likes_el.inner_text()
            likes = self._parse_count(likes_text)

        return XhsNote(
            note_id=note_id,
            title=title.strip() if title else "",
            user_nickname=author.strip() if author else "",
            likes=likes,
            url=f"https://www.xiaohongshu.com/explore/{note_id}",
        )

    async def _extract_from_api(self, page: Page, max_results: int) -> list[XhsNote]:
        """通过监听 API 响应提取数据。"""
        notes = []
        api_response = []

        async def handle_response(response):
            if "/api/sns/web/v1/search/notes" in response.url:
                try:
                    data = await response.json()
                    if data.get("success") and data.get("data", {}).get("items"):
                        api_response.extend(data["data"]["items"])
                except Exception:
                    pass

        page.on("response", handle_response)
        await page.reload(wait_until="networkidle", timeout=self.timeout)
        await asyncio.sleep(3)

        for item in api_response[:max_results]:
            note_card = item.get("note_card", {})
            notes.append(
                XhsNote(
                    note_id=item.get("id", note_card.get("note_id", "")),
                    title=note_card.get("display_title", "无标题"),
                    user_nickname=note_card.get("user", {}).get("nickname", ""),
                    user_id=note_card.get("user", {}).get("user_id", ""),
                    likes=note_card.get("interact_info", {}).get("liked_count", 0),
                    note_type=note_card.get("type", ""),
                    url=f"https://www.xiaohongshu.com/explore/{item.get('id', '')}",
                )
            )

        return notes

    def _parse_count(self, text: str) -> int:
        """解析数量文本（如 "1.2万" -> 12000）。"""
        if not text:
            return 0

        text = text.strip()
        if "万" in text:
            try:
                return int(float(text.replace("万", "")) * 10000)
            except ValueError:
                return 0
        try:
            return int(text)
        except ValueError:
            return 0

    async def get_note_detail(self, note_id: str) -> Optional[XhsNote]:
        """
        获取笔记详情。

        Args:
            note_id: 笔记 ID

        Returns:
            笔记详情
        """
        page = await self._ensure_browser()

        url = f"https://www.xiaohongshu.com/explore/{note_id}"
        await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
        await asyncio.sleep(3)

        # 处理登录弹窗
        await self._handle_login_modal(page)

        try:
            # 提取标题
            title_el = await page.query_selector('#detail-title, .title')
            title = await title_el.inner_text() if title_el else ""

            # 提取内容
            content_el = await page.query_selector('#detail-desc, .desc, .content')
            content = await content_el.inner_text() if content_el else ""

            # 提取作者
            author_el = await page.query_selector('.author-wrapper .username, .user-info .name')
            author = await author_el.inner_text() if author_el else ""

            # 提取互动数据
            likes = 0
            likes_el = await page.query_selector('.like-wrapper .count, [data-type="like"] .count')
            if likes_el:
                likes = self._parse_count(await likes_el.inner_text())

            collects = 0
            collects_el = await page.query_selector('.collect-wrapper .count, [data-type="collect"] .count')
            if collects_el:
                collects = self._parse_count(await collects_el.inner_text())

            comments = 0
            comments_el = await page.query_selector('.chat-wrapper .count, [data-type="chat"] .count')
            if comments_el:
                comments = self._parse_count(await comments_el.inner_text())

            # 提取标签
            tags = []
            tag_elements = await page.query_selector_all('.tag, #hash-tag a')
            for tag_el in tag_elements:
                tag_text = await tag_el.inner_text()
                if tag_text:
                    tags.append(tag_text.strip().lstrip('#'))

            return XhsNote(
                note_id=note_id,
                title=title.strip(),
                content=content.strip(),
                user_nickname=author.strip(),
                likes=likes,
                collects=collects,
                comments=comments,
                tags=tags,
                url=url,
            )

        except Exception as e:
            print(f"获取笔记详情失败: {e}")
            return None

    async def crawl(self, url: str, **kwargs) -> CrawlResult:
        """
        实现 BaseCrawler 接口。

        Args:
            url: 小红书笔记 URL 或搜索关键词

        Returns:
            抓取结果
        """
        try:
            # 如果是搜索关键词
            if not url.startswith("http"):
                notes = await self.search(url, max_results=kwargs.get("max_results", 10))
                markdown = self._notes_to_markdown(notes)
                return CrawlResult(
                    url=f"xhs://search/{url}",
                    markdown=markdown,
                    success=True,
                    metadata={"notes_count": len(notes), "notes": [n.to_dict() for n in notes]},
                )

            # 如果是笔记 URL
            match = re.search(r'/explore/([a-f0-9]+)', url)
            if match:
                note_id = match.group(1)
                note = await self.get_note_detail(note_id)
                if note:
                    markdown = self._note_to_markdown(note)
                    return CrawlResult(
                        url=url,
                        markdown=markdown,
                        success=True,
                        metadata={"note": note.to_dict()},
                    )

            return CrawlResult(url=url, markdown="", success=False, error="Invalid URL")

        except Exception as e:
            return CrawlResult(url=url, markdown="", success=False, error=str(e))

    async def crawl_many(self, urls: list[str], **kwargs) -> list[CrawlResult]:
        """批量抓取。"""
        results = []
        for url in urls:
            result = await self.crawl(url, **kwargs)
            results.append(result)
            await asyncio.sleep(1)  # 避免请求过快
        return results

    def _notes_to_markdown(self, notes: list[XhsNote]) -> str:
        """将笔记列表转换为 Markdown。"""
        lines = [f"# 小红书搜索结果\n\n共找到 {len(notes)} 条笔记\n"]

        for i, note in enumerate(notes, 1):
            lines.append(f"## {i}. {note.title}\n")
            lines.append(f"- 作者: {note.user_nickname}")
            lines.append(f"- 点赞: {note.likes}")
            lines.append(f"- 链接: {note.url}")
            if note.content:
                lines.append(f"\n{note.content[:200]}...")
            lines.append("")

        return "\n".join(lines)

    def _note_to_markdown(self, note: XhsNote) -> str:
        """将单条笔记转换为 Markdown。"""
        lines = [
            f"# {note.title}\n",
            f"作者: {note.user_nickname}",
            f"点赞: {note.likes} | 收藏: {note.collects} | 评论: {note.comments}",
            "",
        ]

        if note.tags:
            lines.append(f"标签: {', '.join(note.tags)}")
            lines.append("")

        if note.content:
            lines.append("---\n")
            lines.append(note.content)

        lines.append(f"\n---\n来源: {note.url}")

        return "\n".join(lines)

    async def close(self):
        """关闭浏览器。"""
        if self._page:
            await self._page.close()
            self._page = None
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
