"""
定时任务模块
使用 APScheduler 管理爬取和发布任务
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from ..config import config
from ..storage.database import Database
from ..xactions.scraper import TweetScraper
from ..xactions.automator import TwitterAutomator
from ..ai.persona import PersonaDistiller
from ..ai.generator import ContentGenerator


class TaskScheduler:
    """任务调度器"""

    def __init__(self, db: Database):
        self.db = db
        self.scheduler = AsyncIOScheduler()
        self.scraper = TweetScraper(db)
        self.automator = TwitterAutomator(db)
        self.distiller = PersonaDistiller(db)
        self.generator = ContentGenerator(db)

    def setup_tasks(self):
        """配置所有定时任务"""
        # 任务1: 定时爬取目标用户推文
        self.scheduler.add_job(
            self.crawl_task,
            'cron',
            hour=12,
            minute=0,
            id='daily_crawl',
            name='每日爬取推文'
        )

        # 任务2: 定时生成并发布推文
        post_interval = config.post_interval_hours
        self.scheduler.add_job(
            self.post_task,
            'interval',
            hours=post_interval,
            id='auto_post',
            name=f'每{post_interval}小时自动发帖'
        )

        logger.info("定时任务配置完成")

    async def crawl_task(self):
        """爬取任务"""
        try:
            target_users = config.target_users

            if not target_users:
                logger.warning("没有配置目标用户，跳过爬取任务")
                return

            logger.info(f"开始执行爬取任务，目标用户: {target_users}")

            for username in target_users:
                try:
                    # 爬取推文
                    await self.scraper.scrape_user(username, count=100)

                    # 蒸馏人格
                    await self.distiller.analyze_user(username)

                    logger.info(f"用户 @{username} 数据处理完成")

                except Exception as e:
                    logger.error(f"处理用户 @{username} 失败: {str(e)}")
                    continue

            logger.info("爬取任务执行完成")

        except Exception as e:
            logger.error(f"爬取任务执行失败: {str(e)}")

    async def post_task(self):
        """发布任务"""
        try:
            logger.info("开始执行发布任务")

            # 获取最新的人格数据
            persona = await self.db.get_latest_persona()

            if persona is None:
                logger.warning("没有可用的人格数据，跳过发布任务")
                return

            # 生成推文（带图片）
            content, image_path = await self.generator.generate_tweet(persona)

            # 发布推文
            await self.automator.post_tweet(content, image_path)

            logger.info("发布任务执行完成")

        except Exception as e:
            logger.error(f"发布任务执行失败: {str(e)}")

    def start(self):
        """启动调度器"""
        logger.info("启动任务调度器")
        self.scheduler.start()

    def shutdown(self):
        """关闭调度器"""
        logger.info("关闭任务调度器")
        self.scheduler.shutdown()
