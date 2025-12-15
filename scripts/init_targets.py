#!/usr/bin/env python3
"""Initialize default crawl targets for major tech companies.

This script populates the database with pre-configured crawl targets
for major Chinese and international tech companies.

Usage:
    python scripts/init_targets.py           # Add all default targets
    python scripts/init_targets.py --list    # List current targets
    python scripts/init_targets.py --clear   # Clear all targets
"""

import argparse
import sys
from pathlib import Path

from offer_sherlock.database import DatabaseManager, CrawlTargetRepository


# Default crawl targets - verified working URLs
DEFAULT_TARGETS = [
    # 国内大厂 - 社招/技术岗
    {
        "company": "腾讯",
        "url": "https://careers.tencent.com/search.html?pcid=40001",
        "crawler_type": "official",
        "description": "腾讯招聘 - 技术类岗位",
    },
    {
        "company": "字节跳动",
        "url": "https://jobs.bytedance.com/experienced/position",
        "crawler_type": "official",
        "description": "字节跳动社招",
    },
    {
        "company": "阿里云",
        "url": "https://careers.aliyun.com/off-campus/position-list",
        "crawler_type": "official",
        "description": "阿里云社招",
    },
    {
        "company": "华为",
        "url": "https://career.huawei.com/reccampportal/portal5/campus-recruitment.html",
        "crawler_type": "official",
        "description": "华为校园招聘",
    },
    {
        "company": "百度",
        "url": "https://talent.baidu.com/external/baidu/index.html#/social",
        "crawler_type": "official",
        "description": "百度社招",
    },
    {
        "company": "美团",
        "url": "https://zhaopin.meituan.com/web/position",
        "crawler_type": "official",
        "description": "美团招聘",
    },
    {
        "company": "京东",
        "url": "https://zhaopin.jd.com/web/job/job_info_list/3",
        "crawler_type": "official",
        "description": "京东招聘 - 技术类",
    },
    {
        "company": "拼多多",
        "url": "https://careers.pinduoduo.com/jobs",
        "crawler_type": "official",
        "description": "拼多多招聘",
    },
    {
        "company": "小红书",
        "url": "https://job.xiaohongshu.com/social/position",
        "crawler_type": "official",
        "description": "小红书社招",
    },
    {
        "company": "B站",
        "url": "https://jobs.bilibili.com/social/positions",
        "crawler_type": "official",
        "description": "哔哩哔哩社招",
    },
    {
        "company": "滴滴",
        "url": "https://talent.didiglobal.com/social",
        "crawler_type": "official",
        "description": "滴滴社招",
    },
]


def init_targets(db: DatabaseManager, targets: list[dict]) -> int:
    """Initialize crawl targets in database.

    Args:
        db: Database manager.
        targets: List of target configurations.

    Returns:
        Number of targets added.
    """
    added = 0

    with db.session() as session:
        repo = CrawlTargetRepository(session)

        for target in targets:
            # Check if already exists
            existing = repo.list_by_company(target["company"])
            url_exists = any(t.url == target["url"] for t in existing)

            if url_exists:
                print(f"  ⏭️  {target['company']} - 已存在")
                continue

            repo.add(
                company=target["company"],
                url=target["url"],
                crawler_type=target.get("crawler_type", "official"),
                is_active=True,
            )
            print(f"  ✅ {target['company']} - {target.get('description', '')}")
            added += 1

    return added


def list_targets(db: DatabaseManager):
    """List all crawl targets."""
    with db.session() as session:
        repo = CrawlTargetRepository(session)
        targets = repo.list_all()

        if not targets:
            print("(无抓取目标)")
            return

        print(f"\n{'公司':<12} {'状态':<6} {'类型':<10} URL")
        print("-" * 80)

        for t in targets:
            status = "✅ 活跃" if t.is_active else "⏸️ 暂停"
            print(f"{t.company:<12} {status:<6} {t.crawler_type:<10} {t.url[:45]}...")


def clear_targets(db: DatabaseManager):
    """Clear all crawl targets."""
    with db.session() as session:
        repo = CrawlTargetRepository(session)
        targets = repo.list_all()

        for t in targets:
            repo.delete(t.id)

        print(f"已删除 {len(targets)} 个抓取目标")


def main():
    parser = argparse.ArgumentParser(
        description="初始化抓取目标",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="列出当前所有抓取目标",
    )
    parser.add_argument(
        "--clear", "-c",
        action="store_true",
        help="清空所有抓取目标",
    )
    parser.add_argument(
        "--db",
        default="data/offers.db",
        help="数据库路径 (默认: data/offers.db)",
    )

    args = parser.parse_args()

    # Ensure data directory exists
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)

    # Initialize database
    db = DatabaseManager(db_path=args.db)
    db.create_tables()

    if args.list:
        print("\n📋 当前抓取目标")
        print("=" * 80)
        list_targets(db)

    elif args.clear:
        print("\n🗑️  清空抓取目标")
        print("=" * 80)
        clear_targets(db)

    else:
        print("\n🚀 初始化默认抓取目标")
        print("=" * 80)
        print(f"数据库: {args.db}")
        print(f"目标数: {len(DEFAULT_TARGETS)}\n")

        added = init_targets(db, DEFAULT_TARGETS)

        print(f"\n✅ 完成！新增 {added} 个目标")
        print("\n运行以下命令开始抓取:")
        print(f"  python scripts/run_agent.py --all --db {args.db}")


if __name__ == "__main__":
    main()
