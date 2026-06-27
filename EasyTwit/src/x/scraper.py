"""
推文爬取模块
使用 XDK 搜索和收集目标用户的推文
"""
from typing import List, Optional
from datetime import datetime
from loguru import logger

from .client import XClient
from ..storage.database import Database
from ..storage.models import Tweet


class TweetScraper:
    """推文爬取器 — 使用 XDK 搜索并收集推文"""

    def __init__(self, db: Database, client: Optional[XClient] = None):
        self.db = db
        self.client = client or XClient()

    async def scrape_user(self, username: str, limit: int = 100) -> List[Tweet]:
        """爬取指定用户的推文

        Args:
            username: X 用户名（不带 @）
            limit: 最大爬取数量

        Returns:
            收集到的推文列表
        """
        logger.info(f"开始爬取 @{username} 的推文, limit={limit}")

        # 先获取用户 ID，再用 user_posts 直接拉取
        raw_tweets = None
        user = self.client.user_info(username)
        if user and user.get('id'):
            raw_tweets = self.client.user_posts(user['id'], count=limit)

        # fallback: 搜索
        if not raw_tweets:
            logger.info(f"user_posts 无结果，改用搜索")
            raw_tweets = self.client.search_user(username, count=limit)

        if not raw_tweets:
            logger.warning(f"未找到 @{username} 的推文")
            return []
            return []

        # 解析推文
        tweets = self._parse_tweets(raw_tweets, username, source='crawl')

        # 去重并保存
        unique = self._deduplicate(tweets)
        if unique:
            await self.db.save_tweets(unique)
            logger.info(f"爬取完成 @{username}: 收集 {len(unique)} 条推文")

        return unique

    async def scrape_users(self, usernames: List[str],
                           limit_per_user: int = 100) -> List[Tweet]:
        """爬取多个用户的推文

        Args:
            usernames: 用户名列表
            limit_per_user: 每个用户最大数量
        """
        all_tweets = []
        for username in usernames:
            try:
                tweets = await self.scrape_user(username, limit=limit_per_user)
                all_tweets.extend(tweets)
            except Exception as e:
                logger.error(f"爬取 @{username} 失败: {e}")
                continue

        return all_tweets

    # ── 解析 ──────────────────────────────────────────────

    def _parse_tweets(self, raw: List[dict], username: str,
                      source: str = 'crawl') -> List[Tweet]:
        """解析 X API 返回的原始推文数据"""
        tweets: List[Tweet] = []

        for item in raw:
            try:
                # X API v2 返回格式
                tweet_id = str(
                    item.get('id')
                    or item.get('tweet_id')
                    or item.get('conversation_id')
                    or ''
                )

                content = (
                    item.get('text')
                    or item.get('content')
                    or item.get('note_tweet', {}).get('text', '')
                    or ''
                )

                if not tweet_id or not content:
                    continue

                # 时间解析
                created_at = None
                raw_time = (
                    item.get('created_at')
                    or item.get('createdAt')
                    or item.get('timestamp')
                )
                if raw_time:
                    try:
                        # ISO 8601 格式: 2024-01-01T00:00:00.000Z
                        if isinstance(raw_time, str):
                            raw_time = raw_time.replace('Z', '+00:00')
                            created_at = datetime.fromisoformat(raw_time)
                        elif isinstance(raw_time, (int, float)):
                            created_at = datetime.fromtimestamp(raw_time)
                    except (ValueError, TypeError):
                        pass

                # 互动数据
                metrics = item.get('public_metrics', {})
                likes = int(metrics.get('like_count', item.get('likes', item.get('favorite_count', 0))))
                retweets = int(metrics.get('retweet_count', item.get('retweets', item.get('retweet_count', 0))))
                replies = int(metrics.get('reply_count', item.get('replies', item.get('reply_count', 0))))

                tweets.append(Tweet(
                    tweet_id=tweet_id,
                    username=username,
                    content=content,
                    created_at=created_at,
                    likes=likes,
                    retweets=retweets,
                    replies=replies,
                    source=source,
                ))

            except Exception as e:
                logger.warning(f"解析推文失败: {e}")
                continue

        return tweets

    def _deduplicate(self, tweets: List[Tweet]) -> List[Tweet]:
        """按 tweet_id 去重"""
        seen: set = set()
        unique: List[Tweet] = []
        for t in tweets:
            if t.tweet_id not in seen:
                seen.add(t.tweet_id)
                unique.append(t)
        return unique
