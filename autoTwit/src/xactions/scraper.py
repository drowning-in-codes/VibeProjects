"""
推文爬取模块
"""
from typing import List
from datetime import datetime
from loguru import logger

from .client import XActionsClient
from ..storage.models import Tweet, User
from ..storage.database import Database


class TweetScraper:
    """推文爬取器"""

    def __init__(self, db: Database):
        self.client = XActionsClient()
        self.db = db

    async def scrape_user(self, username: str, count: int = 100) -> List[Tweet]:
        """爬取用户推文并保存到数据库"""
        try:
            # 获取用户信息
            profile = await self.client.get_user_profile(username)

            user = User(
                username=username,
                display_name=profile.get('name'),
                bio=profile.get('bio'),
                followers_count=profile.get('followers_count', 0),
                following_count=profile.get('following_count', 0),
                created_at=datetime.now()
            )
            await self.db.save_user(user)

            # 爬取推文
            tweet_data = await self.client.scrape_user_tweets(username, count)

            tweets = []
            for item in tweet_data:
                tweet = Tweet(
                    tweet_id=item.get('id'),
                    username=username,
                    content=item.get('text', ''),
                    created_at=datetime.fromisoformat(item.get('created_at', datetime.now().isoformat())),
                    likes=item.get('favorite_count', 0),
                    retweets=item.get('retweet_count', 0),
                    replies=item.get('reply_count', 0)
                )
                tweets.append(tweet)

            # 保存到数据库
            await self.db.save_tweets(tweets)

            logger.info(f"成功爬取并保存 @{username} 的 {len(tweets)} 条推文")
            return tweets

        except Exception as e:
            logger.error(f"爬取用户 @{username} 推文失败: {str(e)}")
            raise
