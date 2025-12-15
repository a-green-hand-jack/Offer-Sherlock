#!/usr/bin/env python3
"""测试小红书 SDK 是否正常工作。

xhs SDK 使用 xhs.help.sign 进行签名，这是一个纯 Python 实现。
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_with_sign():
    """使用 xhs.help.sign 进行测试。"""
    from xhs import XhsClient
    from xhs.help import sign

    cookie = os.getenv("XHS_COOKIE")
    if not cookie:
        print("❌ 未找到 XHS_COOKIE 环境变量")
        return False, None

    print("🔍 初始化 XhsClient...")
    print(f"   Cookie: {cookie[:50]}...")

    try:
        # sign 函数签名: (uri, data=None, ctime=None, a1='', b1='')
        # XhsClient._pre_headers 调用: external_sign(url, data, a1=..., web_session=...)

        # 创建一个适配器函数
        def sign_adapter(uri, data=None, a1="", web_session="", **kwargs):
            """适配 XhsClient 的签名调用。"""
            return sign(uri, data, a1=a1)

        # 创建客户端
        client = XhsClient(cookie=cookie, sign=sign_adapter)

        # 测试 1: 获取首页推荐（不需要特殊权限）
        print("\n📰 获取首页推荐...")
        try:
            from xhs import FeedType
            home_feed = client.get_home_feed(FeedType.RECOMMEND)
            if home_feed and "items" in home_feed:
                print(f"   ✅ 首页推荐获取成功，共 {len(home_feed['items'])} 条")
            else:
                print(f"   ⚠️ 首页推荐返回: {str(home_feed)[:100]}")
        except Exception as e:
            print(f"   ❌ 首页推荐失败: {e}")

        # 测试 2: 搜索笔记
        keyword = "互联网 offer"
        print(f"\n🔍 搜索关键词: {keyword}")

        notes = client.get_note_by_keyword(keyword)

        if notes and "items" in notes:
            items = notes["items"]
            print(f"✅ 找到 {len(items)} 条笔记\n")

            for i, item in enumerate(items[:5], 1):
                note_card = item.get("note_card", {})
                title = note_card.get("display_title", "无标题")
                user = note_card.get("user", {}).get("nickname", "未知用户")
                liked_count = note_card.get("interact_info", {}).get("liked_count", 0)
                note_id = note_card.get("note_id", "")

                print(f"[{i}] {title[:50]}...")
                print(f"    作者: {user} | 点赞: {liked_count}")
                print(f"    note_id: {note_id}")
                print()

            return True, items
        else:
            print("❌ 搜索返回空结果或错误")
            if notes:
                print(f"返回内容: {notes}")
            return False, None

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_get_user_info():
    """测试获取当前用户信息。"""
    from xhs import XhsClient
    from xhs.help import sign

    cookie = os.getenv("XHS_COOKIE")
    if not cookie:
        return False

    def sign_adapter(uri, data=None, a1="", web_session="", **kwargs):
        return sign(uri, data, a1=a1)

    client = XhsClient(cookie=cookie, sign=sign_adapter)

    print("\n👤 获取当前用户信息...")
    try:
        user_info = client.get_self_info()
        if user_info:
            nickname = user_info.get("nickname", "未知")
            user_id = user_info.get("user_id", "未知")
            print(f"   ✅ 用户: {nickname} (ID: {user_id})")
            return True
        else:
            print("   ❌ 获取用户信息失败")
            return False
    except Exception as e:
        print(f"   ❌ 错误: {e}")
        return False


def test_direct_request():
    """直接测试签名和请求。"""
    import requests
    from xhs.help import sign, cookie_str_to_cookie_dict

    cookie = os.getenv("XHS_COOKIE")
    if not cookie:
        return False

    cookie_dict = cookie_str_to_cookie_dict(cookie)
    a1 = cookie_dict.get("a1", "")

    print("\n🔧 直接测试签名和请求...")
    print(f"   a1: {a1[:20]}...")

    # 测试签名
    uri = "/api/sns/web/v1/homefeed"
    data = {"cursor_score": "", "num": 20, "refresh_type": 1}

    sign_result = sign(uri, data, a1=a1)
    print(f"   签名结果: x-s={sign_result['x-s'][:20]}..., x-t={sign_result['x-t']}")

    # 构建请求
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://www.xiaohongshu.com",
        "Referer": "https://www.xiaohongshu.com/",
        "Cookie": cookie,
        "x-s": sign_result["x-s"],
        "x-t": sign_result["x-t"],
        "x-s-common": sign_result["x-s-common"],
    }

    try:
        import json
        resp = requests.post(
            f"https://edith.xiaohongshu.com{uri}",
            headers=headers,
            json=data,
            timeout=10
        )
        result = resp.json()
        print(f"   响应状态: {resp.status_code}")
        print(f"   响应内容: {json.dumps(result, ensure_ascii=False)[:200]}")

        if result.get("success"):
            print("   ✅ 直接请求成功!")
            return True
        else:
            print(f"   ❌ 请求失败: code={result.get('code')}, msg={result.get('msg')}")
            return False
    except Exception as e:
        print(f"   ❌ 请求异常: {e}")
        return False


def main():
    """主函数。"""
    print("=" * 60)
    print("🧪 小红书 SDK 测试")
    print("=" * 60)

    # 测试 0: 直接请求测试
    print("\n" + "-" * 60)
    print("测试 0: 直接签名请求")
    print("-" * 60)
    direct_ok = test_direct_request()

    # 测试 1: 获取用户信息
    print("\n" + "-" * 60)
    print("测试 1: 获取用户信息")
    print("-" * 60)
    user_ok = test_get_user_info()

    # 测试 2: 搜索功能
    print("\n" + "-" * 60)
    print("测试 2: 搜索笔记")
    print("-" * 60)
    search_ok, items = test_with_sign()

    # 总结
    print("\n" + "=" * 60)
    print("📊 测试结果")
    print("=" * 60)
    print(f"   直接请求: {'✅ 通过' if direct_ok else '❌ 失败'}")
    print(f"   用户信息: {'✅ 通过' if user_ok else '❌ 失败'}")
    print(f"   搜索功能: {'✅ 通过' if search_ok else '❌ 失败'}")

    if direct_ok or user_ok or search_ok:
        print("\n🎉 XHS SDK 可以使用（部分功能）")
    else:
        print("\n⚠️ 所有测试失败")
        print("\n可能的原因：")
        print("1. Cookie 已过期，需要重新获取")
        print("2. 账号被风控，需要在浏览器中验证")
        print("3. IP 被封，需要更换网络或使用代理")


if __name__ == "__main__":
    main()
