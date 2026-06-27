"""
推文发布模块
整合 AI 生成 + 图片 + X 发布
"""
import asyncio
from typing import Optional, Tuple
from datetime import datetime
from loguru import logger

from .config import config
from .x.client import XClient
from .ai.generator import ContentGenerator
from .storage.database import Database
from .storage.models import Persona, PostHistory


class Poster:
    """推文发布器 — 生成内容并发布到 X"""

    def __init__(self, db: Database):
        self.db = db
        self.x = XClient()
        self.generator = ContentGenerator(db)

    async def post(
        self,
        persona: Optional[Persona] = None,
        topic: Optional[str] = None,
        with_image: Optional[bool] = None,
        dry_run: bool = False,
    ) -> Optional[PostHistory]:
        """生成并发布一条推文

        Args:
            persona: 人格特征（None 则使用最新的）
            topic: 话题关键词
            with_image: 是否配图（None 则自动判断）
            dry_run: 仅生成不发布（用于预览）

        Returns:
            发布记录，失败返回 None
        """
        # 检查每日限额
        posts_today = await self.db.get_posts_today()
        max_posts = config.max_posts_per_day
        if posts_today >= max_posts:
            logger.warning(
                f"已达每日限额 ({posts_today}/{max_posts})，跳过发布"
            )
            return None

        # Step 1: 生成推文内容
        logger.info("=" * 50)
        logger.info(f"开始生成推文 (今日第 {posts_today + 1} 条, 上限 {max_posts})")

        try:
            tweet_content, image_path = await self.generator.generate_tweet(
                persona=persona,
                topic=topic,
                with_image=with_image,
            )
        except Exception as e:
            logger.error(f"推文生成失败: {e}")
            return None

        logger.info(f"推文内容: {tweet_content}")

        # 创建发布记录
        post = PostHistory(
            content=tweet_content,
            image_path=image_path,
            posted_at=datetime.now(),
            status="pending",
        )

        if dry_run:
            logger.info("DRY RUN — 不实际发布到 X")
            post.status = "dry_run"
            post_id = await self.db.save_post(post)
            post.id = post_id
            return post

        # Step 2: 上传媒体（如有图片，只给第一条推文配图）
        media_ids = None
        if image_path:
            media_id = self.x.upload_media(image_path)
            if media_id:
                media_ids = [media_id]
            else:
                logger.warning("媒体上传失败，将以纯文本发布")

        # Step 3: 发布到 X（过长内容自动拆成推文串）
        try:
            result = await self._post_thread(tweet_content, media_ids=media_ids)

            post.status = "success"
            post.tweet_id = result['root_id']
            post_id = await self.db.save_post(post)
            post.id = post_id

            thread_info = f" (thread: {result.get('count', 1)} 条)" if result.get('count', 1) > 1 else ""
            logger.success(f"推文发布成功! ID: {result['root_id']}{thread_info}")
            return post

        except Exception as e:
            logger.error(f"推文发布失败: {e}")
            post.status = "failed"
            post.error_message = str(e)
            await self.db.save_post(post)
            return post

    async def post_now(
        self,
        username: Optional[str] = None,
        topic: Optional[str] = None,
        with_image: Optional[bool] = None,
        dry_run: bool = False,
    ) -> Optional[PostHistory]:
        """快速发布：自动获取人格并发布

        Args:
            username: 指定使用某人的人格（None 则使用最新的）
            topic: 话题
            with_image: 是否配图
            dry_run: 仅预览
        """
        persona = None
        if username:
            persona = await self.db.get_persona(username)
            if not persona:
                logger.error(f"未找到 @{username} 的人格数据")
                return None

        return await self.post(
            persona=persona,
            topic=topic,
            with_image=with_image,
            dry_run=dry_run,
        )

    async def _post_thread(self, content: str, media_ids: list = None) -> dict:
        """发布推文，过长则自动拆分 thread"""
        from .ai.generator import ContentGenerator
        chunks = ContentGenerator.split_thread(content)

        # 发布第一条
        result = self.x.post(chunks[0], media_ids=media_ids)
        root_id = result.get('tweet_id', '')

        # 逐条回复
        for chunk in chunks[1:]:
            try:
                import asyncio
                await asyncio.sleep(1)
                reply = self.x.reply(root_id, chunk)
                if not root_id:
                    root_id = reply.get('tweet_id', '')
            except Exception as e:
                logger.error(f"Thread 回复失败: {e}")

        return {"root_id": root_id, "count": len(chunks)}

    async def post_thread(
        self,
        tweets_count: int = 3,
        persona: Optional[Persona] = None,
        topic: Optional[str] = None,
    ) -> list:
        """发布推文串 (thread)

        Args:
            tweets_count: 推文数量
            persona: 人格
            topic: 话题

        Returns:
            发布记录列表
        """
        results = []
        for i in range(tweets_count):
            logger.info(f"生成第 {i + 1}/{tweets_count} 条推文...")
            result = await self.post(persona=persona, topic=topic, with_image=False)
            if result and result.status == "success":
                results.append(result)
            else:
                logger.warning(f"第 {i + 1} 条推文失败，停止生成后续")
                break

            # 简短间隔
            if i < tweets_count - 1:
                await asyncio.sleep(2)

        logger.info(f"推文串发布完成: {len(results)}/{tweets_count} 条成功")
        return results
