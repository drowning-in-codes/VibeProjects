"""
EasyTwit 爬取功能测试
测试 scrape sources: users / following / timeline
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.x.client import XClient
from src.x.scraper import TweetScraper
from src.storage.database import Database
from src.storage.models import Tweet


async def test_scrape_source(source: str):
    """测试指定来源的爬取"""
    db = Database("./data/test_scrape.db")
    await db.initialize()
    scraper = TweetScraper(db)

    print(f"\n  [{source}] ", end="")

    try:
        if source == "following":
            tweets = await scraper.scrape_following(limit_per_user=5)
        elif source == "timeline":
            tweets = await scraper.scrape_timeline(count=20)
        elif source == "users":
            users = config.target_users
            if not users:
                print("SKIP (no users configured)")
                return
            tweets = await scraper.scrape_users(users, limit_per_user=5)
        else:
            print(f"UNKNOWN source: {source}")
            return

        print(f"{len(tweets)} tweets")
    except Exception as e:
        msg = str(e)[:100]
        if "402" in msg or "Payment" in msg:
            print("402 Payment Required (need Basic tier)")
        else:
            print(f"Error: {msg}")


async def test_xclient_methods():
    """测试 XClient 方法返回值类型"""
    print("\n--- XClient methods ---")
    x = XClient()
    print(f"  ready: {x.ready}")

    if not x.ready:
        print("  SKIP: X client not ready")
        return

    # following
    try:
        f = x.following(count=5)
        print(f"  following(): list[{len(f)}]")
        if f:
            print(f"    first: @{f[0].get('username', '?')}")
    except Exception as e:
        msg = str(e)[:80]
        print(f"  following(): {msg}")

    # timeline
    try:
        t = x.timeline(count=5)
        print(f"  timeline(): list[{len(t)}]")
        if t:
            print(f"    first: {t[0].get('text', t[0].get('id', '?'))[:50]}")
    except Exception as e:
        msg = str(e)[:80]
        print(f"  timeline(): {msg}")

    # user_info
    try:
        u = x.user_info("X")
        print(f"  user_info('X'): {u is not None}")
    except Exception as e:
        msg = str(e)[:80]
        print(f"  user_info('X'): {msg}")


async def main():
    print("=" * 50)
    print("EasyTwit Scrape Test")
    print(f"scrape_source: {config.scrape_source}")
    print(f"target_users: {config.target_users or '(none)'}")
    print("=" * 50)

    await test_xclient_methods()

    print("\n--- Scrape sources ---")
    for source in ["users", "following", "timeline"]:
        await test_scrape_source(source)

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
