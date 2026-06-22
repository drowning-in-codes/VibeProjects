"""
自动化操作模块
"""
from typing import Optional
from loguru import logger

from .client import XActionsClient
from ..storage.database import Database


class TwitterAutomator:
    """Twitter 自动化操作"""

    def __init__(self, db: Database):
        self.client = XActionsClient()
        self.db = db

    async def post_tweet(self, content: str, image_path: Optional[str] = None) -> Optional[str]:
        """发布推文（支持图片）"""
        try:
            result = await self.client.post_tweet(content, image_path)
            tweet_id = result.get('tweet_id')

            # 保存到发布历史
            await self.db.save_post_history(
                content=content,
                tweet_id=tweet_id,
                status='success'
            )

            logger.info(f"推文发布成功: {content[:50]}...")
            if image_path:
                logger.info(f"  附带图片: {image_path}")
            return tweet_id

        except Exception as e:
            logger.error(f"发布推文失败: {str(e)}")
            await self.db.save_post_history(
                content=content,
                status='failed'
            )
            raise

    async def like_tweet(self, tweet_id: str) -> bool:
        """点赞推文"""
        try:
            success = await self.client.like_tweet(tweet_id)
            if success:
                logger.info(f"点赞成功: {tweet_id}")
            return success
        except Exception as e:
            logger.error(f"点赞失败: {str(e)}")
            return False

    async def follow_user(self, username: str) -> bool:
        """关注用户"""
        try:
            success = await self.client.follow_user(username)
            if success:
                logger.info(f"关注成功: @{username}")
            return success
        except Exception as e:
            logger.error(f"关注失败: {str(e)}")
            return False
