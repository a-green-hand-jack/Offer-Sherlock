#!/usr/bin/env python3
"""
使用 Playwright 浏览器直接访问小红书搜索页面获取数据。

这种方式需要先登录，然后在同一会话中进行搜索。
"""

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from playwright.async_api import async_playwright


async def search_xhs_with_login(keyword: str, max_results: int = 10):
    """登录后搜索小红书笔记。"""

    print("=" * 60)
    print("🔍 小红书浏览器搜索")
    print("=" * 60)
    print()
    print("1. 浏览器将打开小红书")
    print("2. 请登录（如果需要）")
    print("3. 登录后脚本会自动搜索并提取结果")
    print()

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,  # 显示浏览器方便登录
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        page = await context.new_page()

        # 访问首页
        print("🌐 打开小红书首页...")
        await page.goto("https://www.xiaohongshu.com", wait_until="domcontentloaded")
        await asyncio.sleep(2)

        # 检查登录状态，等待用户登录
        print("\n⏳ 检测登录状态...")
        print("   如果需要登录，请在浏览器中完成登录")
        print("   最长等待 3 分钟\n")

        max_wait = 180
        waited = 0
        while waited < max_wait:
            cookies = await context.cookies()
            cookie_names = [c["name"] for c in cookies]
            if "web_session" in cookie_names:
                print("✅ 已登录！")
                break
            await asyncio.sleep(2)
            waited += 2
            if waited % 30 == 0:
                print(f"   等待中... ({waited}秒)")
        else:
            print("❌ 登录超时")
            await browser.close()
            return []

        # 等待一下确保状态稳定
        await asyncio.sleep(2)

        # 执行搜索
        print(f"\n🔍 搜索: {keyword}")
        encoded_keyword = quote(keyword)
        search_url = f"https://www.xiaohongshu.com/search_result?keyword={encoded_keyword}&source=web_search_result_notes"

        await page.goto(search_url, wait_until="domcontentloaded")
        print("   等待搜索结果加载...")
        await asyncio.sleep(3)

        # 检查是否弹出登录框
        login_modal = await page.query_selector('text="登录后查看搜索结果"')
        if login_modal:
            print("\n⚠️ 需要登录才能查看搜索结果")
            print("   请在浏览器中完成登录（扫码或手机号）")
            print("   等待登录完成...\n")

            # 等待登录框消失
            max_wait = 120
            waited = 0
            while waited < max_wait:
                login_modal = await page.query_selector('text="登录后查看搜索结果"')
                if not login_modal:
                    print("✅ 登录成功！")
                    await asyncio.sleep(3)
                    break
                await asyncio.sleep(2)
                waited += 2
                if waited % 20 == 0:
                    print(f"   等待中... ({waited}秒)")
            else:
                print("❌ 登录超时")

        # 等待内容加载
        await asyncio.sleep(3)

        # 滚动页面触发懒加载
        await page.evaluate("window.scrollTo(0, 500)")
        await asyncio.sleep(2)

        # 保存截图
        screenshot_path = Path("data/xhs_search_result.png")
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(screenshot_path))
        print(f"   截图已保存: {screenshot_path}")

        # 提取搜索结果
        print("\n📖 提取搜索结果...")

        notes = []

        # 方法1: 从 __INITIAL_STATE__ 提取
        try:
            initial_state = await page.evaluate("""
                () => {
                    if (window.__INITIAL_STATE__) {
                        return JSON.stringify(window.__INITIAL_STATE__);
                    }
                    return null;
                }
            """)

            if initial_state:
                data = json.loads(initial_state)
                # 搜索结果通常在 search.notes 或 feed.notes 中
                search_notes = data.get("search", {}).get("notes", [])
                if not search_notes:
                    search_notes = data.get("feed", {}).get("notes", [])

                for note in search_notes[:max_results]:
                    notes.append({
                        "note_id": note.get("id", ""),
                        "title": note.get("display_title", note.get("title", "无标题")),
                        "user": note.get("user", {}).get("nickname", ""),
                        "likes": note.get("liked_count", 0),
                        "type": note.get("type", ""),
                    })
                print(f"   从 __INITIAL_STATE__ 提取到 {len(notes)} 条")
        except Exception as e:
            print(f"   __INITIAL_STATE__ 提取失败: {e}")

        # 方法2: 从 DOM 元素提取
        if not notes:
            try:
                # 小红书搜索结果的选择器
                note_elements = await page.query_selector_all('section.note-item, div[data-v-a264b01a].note-item, .feeds-page section')

                for elem in note_elements[:max_results]:
                    try:
                        # 获取标题
                        title_el = await elem.query_selector('.title span, .note-content .title, a.title')
                        title = await title_el.inner_text() if title_el else ""

                        # 获取作者
                        author_el = await elem.query_selector('.author-wrapper .name, .user-info .name')
                        author = await author_el.inner_text() if author_el else ""

                        # 获取链接
                        link_el = await elem.query_selector('a[href*="/explore/"]')
                        href = await link_el.get_attribute("href") if link_el else ""

                        if title or href:
                            note_id = ""
                            if href:
                                match = re.search(r'/explore/([a-f0-9]+)', href)
                                if match:
                                    note_id = match.group(1)

                            notes.append({
                                "note_id": note_id,
                                "title": title.strip() if title else "无标题",
                                "user": author.strip() if author else "",
                                "link": f"https://www.xiaohongshu.com{href}" if href else "",
                            })
                    except:
                        continue

                print(f"   从 DOM 提取到 {len(notes)} 条")
            except Exception as e:
                print(f"   DOM 提取失败: {e}")

        # 方法3: 从网络请求中提取
        if not notes:
            print("   尝试刷新页面并捕获 API 响应...")

            api_response = []

            async def handle_response(response):
                if "/api/sns/web/v1/search/notes" in response.url:
                    try:
                        data = await response.json()
                        if data.get("success") and data.get("data", {}).get("items"):
                            api_response.extend(data["data"]["items"])
                    except:
                        pass

            page.on("response", handle_response)
            await page.reload(wait_until="networkidle")
            await asyncio.sleep(3)

            for item in api_response[:max_results]:
                note_card = item.get("note_card", {})
                notes.append({
                    "note_id": item.get("id", note_card.get("note_id", "")),
                    "title": note_card.get("display_title", "无标题"),
                    "user": note_card.get("user", {}).get("nickname", ""),
                    "likes": note_card.get("interact_info", {}).get("liked_count", 0),
                })
            print(f"   从 API 响应提取到 {len(notes)} 条")

        await browser.close()
        return notes


async def main():
    keyword = "字节跳动 面经"
    notes = await search_xhs_with_login(keyword)

    print("\n" + "=" * 60)
    print("📊 搜索结果")
    print("=" * 60)

    if notes:
        print(f"\n找到 {len(notes)} 条笔记:\n")
        for i, note in enumerate(notes, 1):
            print(f"[{i}] {note.get('title', '无标题')[:50]}")
            if note.get('user'):
                print(f"    作者: {note['user']}")
            if note.get('likes'):
                print(f"    点赞: {note['likes']}")
            if note.get('note_id'):
                print(f"    ID: {note['note_id']}")
            print()
    else:
        print("\n❌ 未找到搜索结果")
        print("请检查 data/xhs_search_result.png 截图")


if __name__ == "__main__":
    asyncio.run(main())
