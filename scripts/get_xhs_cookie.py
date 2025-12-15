#!/usr/bin/env python3
"""
小红书 Cookie 获取脚本

使用 Playwright 打开浏览器，让用户登录小红书后自动提取必要的 cookie。
获取的 cookie 会保存到 .env 文件中。

使用方法：
    uv run python scripts/get_xhs_cookie.py

自动模式（等待登录后自动提取）：
    uv run python scripts/get_xhs_cookie.py --auto

必须的 cookie 字段：
    - a1: 设备指纹
    - web_session: 登录会话
    - webId: Web 标识
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("❌ Playwright 未安装，请先运行：")
    print("   uv add playwright")
    print("   uv run playwright install chromium")
    sys.exit(1)


# 必需的 cookie 字段
REQUIRED_COOKIES = ["a1", "web_session", "webId"]

# 可选但有用的 cookie 字段
OPTIONAL_COOKIES = ["web_id", "xsecappid", "gid", "customerClientId"]


async def get_xhs_cookies(auto_mode: bool = False):
    """打开浏览器让用户登录，然后提取 cookie。

    Args:
        auto_mode: 如果为 True，自动等待登录完成后提取 cookie
    """

    print("=" * 60)
    print("🍪 小红书 Cookie 获取工具")
    print("=" * 60)
    print()
    print("即将打开浏览器，请按以下步骤操作：")
    print("1. 浏览器会自动打开小红书登录页面")
    print("2. 使用手机扫码或账号密码登录")
    print("3. 登录成功后，等待页面完全加载")
    if not auto_mode:
        print("4. 回到终端按 Enter 键提取 cookie")
    else:
        print("4. 脚本会自动检测登录状态并提取 cookie")
    print()
    print("⚠️  注意：请勿关闭浏览器窗口！")
    print()

    if not auto_mode:
        input("按 Enter 键开始...")

    async with async_playwright() as p:
        # 启动有头浏览器（用户可见）
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )

        # 创建上下文，模拟真实用户
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="zh-CN",
        )

        # 打开页面
        page = await context.new_page()

        print("\n🌐 正在打开小红书...")
        try:
            await page.goto(
                "https://www.xiaohongshu.com",
                wait_until="domcontentloaded",
                timeout=60000,
            )
        except Exception as e:
            print(f"⚠️ 页面加载警告: {e}")
            print("   继续等待页面...")
            await asyncio.sleep(3)

        print("\n✅ 页面已打开！")
        print()
        print("👆 请在浏览器中完成登录")
        print("   - 点击右上角「登录」按钮")
        print("   - 使用手机 App 扫码登录（推荐）")
        print("   - 或使用手机号验证码登录")
        print()

        if auto_mode:
            # 自动模式：等待 web_session cookie 出现
            print("⏳ 等待登录完成...")
            print("   请在手机上扫码并确认登录")
            print("   最长等待 5 分钟")
            print()
            max_wait = 300  # 最多等待 5 分钟
            waited = 0
            while waited < max_wait:
                cookies = await context.cookies()
                cookie_names = [c["name"] for c in cookies]
                if "web_session" in cookie_names:
                    print("\n✅ 检测到登录 cookie！")
                    print("   等待页面完全加载...")

                    # 刷新页面确保登录状态同步
                    await page.reload(wait_until="domcontentloaded")
                    await asyncio.sleep(3)

                    # 再次获取 cookie（刷新后可能更新）
                    cookies = await context.cookies()
                    break
                await asyncio.sleep(2)
                waited += 2
                if waited % 30 == 0:
                    remaining = (max_wait - waited) // 60
                    print(f"   已等待 {waited} 秒... (剩余 {remaining} 分钟)")
            else:
                print("❌ 登录超时（5分钟），请重试")
                await browser.close()
                return None
        else:
            input("登录完成后，按 Enter 键提取 cookie...")

        # 获取所有 cookie
        cookies = await context.cookies()

        # 提取需要的 cookie
        cookie_dict = {}
        for cookie in cookies:
            if cookie["name"] in REQUIRED_COOKIES + OPTIONAL_COOKIES:
                cookie_dict[cookie["name"]] = cookie["value"]

        # 检查必需的 cookie
        missing = [c for c in REQUIRED_COOKIES if c not in cookie_dict]

        if missing:
            print(f"\n❌ 缺少必需的 cookie: {', '.join(missing)}")
            print("   请确保已经成功登录小红书")

            # 显示获取到的 cookie（调试用）
            print("\n📋 已获取的 cookie:")
            for cookie in cookies:
                print(f"   - {cookie['name']}: {cookie['value'][:20]}...")

            await browser.close()
            return None

        await browser.close()

        print("\n✅ Cookie 提取成功！")
        print()

        # 显示获取到的 cookie
        print("📋 获取到的 cookie:")
        for name, value in cookie_dict.items():
            display_value = value[:30] + "..." if len(value) > 30 else value
            required = "✓" if name in REQUIRED_COOKIES else "○"
            print(f"   [{required}] {name}: {display_value}")

        return cookie_dict


def save_cookies_to_env(cookie_dict: dict):
    """将 cookie 保存到 .env 文件。"""

    env_path = Path(__file__).parent.parent / ".env"

    # 构建 cookie 字符串（用于 XhsClient）
    cookie_str = "; ".join([f"{k}={v}" for k, v in cookie_dict.items()])

    # 读取现有 .env 内容
    existing_content = ""
    if env_path.exists():
        with open(env_path, "r") as f:
            existing_content = f.read()

    # 更新或添加 XHS_COOKIE
    lines = existing_content.strip().split("\n") if existing_content.strip() else []
    new_lines = []
    xhs_cookie_found = False

    for line in lines:
        if line.startswith("XHS_COOKIE="):
            new_lines.append(f'XHS_COOKIE="{cookie_str}"')
            xhs_cookie_found = True
        else:
            new_lines.append(line)

    if not xhs_cookie_found:
        new_lines.append(f'XHS_COOKIE="{cookie_str}"')

    # 写入 .env
    with open(env_path, "w") as f:
        f.write("\n".join(new_lines) + "\n")

    print(f"\n💾 Cookie 已保存到 {env_path}")

    # 同时保存为 JSON（备份）
    json_path = Path(__file__).parent.parent / "data" / "xhs_cookies.json"
    json_path.parent.mkdir(parents=True, exist_ok=True)

    with open(json_path, "w") as f:
        json.dump(cookie_dict, f, indent=2)

    print(f"💾 Cookie JSON 备份已保存到 {json_path}")


def test_cookie():
    """测试 cookie 是否有效。"""
    try:
        from xhs import XhsClient
    except ImportError:
        print("\n⚠️ xhs 库未安装，跳过测试")
        return False

    # 从 .env 读取 cookie
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        print("\n⚠️ .env 文件不存在，跳过测试")
        return False

    cookie = None
    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("XHS_COOKIE="):
                cookie = line.split("=", 1)[1].strip().strip('"')
                break

    if not cookie:
        print("\n⚠️ 未找到 XHS_COOKIE，跳过测试")
        return False

    print("\n🧪 测试 cookie 有效性...")

    try:
        client = XhsClient(cookie=cookie)
        # 尝试获取用户信息
        user_info = client.get_self_info()

        if user_info:
            nickname = user_info.get("nickname", "未知")
            print(f"✅ Cookie 有效！当前用户: {nickname}")
            return True
        else:
            print("❌ Cookie 无效或已过期")
            return False
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


async def main():
    """主函数。"""

    # 解析命令行参数
    parser = argparse.ArgumentParser(description="小红书 Cookie 获取工具")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="自动模式：等待登录完成后自动提取 cookie",
    )
    args = parser.parse_args()

    # 获取 cookie
    cookie_dict = await get_xhs_cookies(auto_mode=args.auto)

    if cookie_dict:
        # 保存 cookie
        save_cookies_to_env(cookie_dict)

        # 测试 cookie
        print()
        test_cookie()

        print()
        print("=" * 60)
        print("🎉 完成！现在可以使用小红书 SDK 了")
        print("=" * 60)
        print()
        print("使用示例：")
        print("  from xhs import XhsClient")
        print("  from dotenv import load_dotenv")
        print("  import os")
        print()
        print("  load_dotenv()")
        print("  client = XhsClient(cookie=os.getenv('XHS_COOKIE'))")
        print("  notes = client.get_note_by_keyword('字节跳动 面经')")
        print()
    else:
        print("\n❌ Cookie 获取失败，请重试")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
