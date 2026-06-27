"""
SQLite 数据库管理模块
"""
import aiosqlite
from pathlib import Path
from typing import List, Optional
from loguru import logger

from .models import Tweet, Persona, PostHistory


class Database:
    """SQLite 数据库管理"""

    def __init__(self, db_path: str = "./data/easytwit.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """初始化数据库表"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            # 推文表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tweets (
                    tweet_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT,
                    likes INTEGER DEFAULT 0,
                    retweets INTEGER DEFAULT 0,
                    replies INTEGER DEFAULT 0,
                    source TEXT DEFAULT '',
                    crawled_at TEXT DEFAULT (datetime('now'))
                )
            """)

            # 人格表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS personas (
                    username TEXT PRIMARY KEY,
                    tone TEXT DEFAULT '',
                    vocabulary TEXT DEFAULT '[]',
                    topics TEXT DEFAULT '[]',
                    style_metrics TEXT DEFAULT '{}',
                    updated_at TEXT,
                    source TEXT DEFAULT 'distilled'
                )
            """)

            # 发布历史表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS post_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    image_path TEXT,
                    posted_at TEXT,
                    tweet_id TEXT,
                    status TEXT DEFAULT 'pending',
                    error_message TEXT
                )
            """)

            # 创建索引
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_tweets_username
                ON tweets(username)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_post_history_status
                ON post_history(status)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_post_history_posted_at
                ON post_history(posted_at)
            """)

            await db.commit()
            logger.info(f"数据库初始化完成: {self.db_path}")

    # ── Tweet CRUD ────────────────────────────────────────

    async def save_tweet(self, tweet: Tweet):
        """保存推文（重复 tweet_id 则忽略）"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            await db.execute("""
                INSERT OR IGNORE INTO tweets
                (tweet_id, username, content, created_at, likes, retweets, replies, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                tweet.tweet_id, tweet.username, tweet.content,
                tweet.created_at.isoformat() if tweet.created_at else None,
                tweet.likes, tweet.retweets, tweet.replies, tweet.source
            ))
            await db.commit()

    async def save_tweets(self, tweets: List[Tweet]):
        """批量保存推文"""
        for tweet in tweets:
            await self.save_tweet(tweet)

    async def get_user_tweets(self, username: str, limit: int = 200) -> List[Tweet]:
        """获取指定用户的推文"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM tweets
                WHERE username = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (username, limit))
            rows = await cursor.fetchall()
            return [Tweet.from_dict(dict(row)) for row in rows]

    async def get_all_tweets(self, limit: int = 200) -> List[Tweet]:
        """获取所有推文"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM tweets
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            rows = await cursor.fetchall()
            return [Tweet.from_dict(dict(row)) for row in rows]

    async def get_tweet_count(self, username: Optional[str] = None) -> int:
        """获取推文数量"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            if username:
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM tweets WHERE username = ?",
                    (username,)
                )
            else:
                cursor = await db.execute("SELECT COUNT(*) FROM tweets")
            row = await cursor.fetchone()
            return row[0] if row else 0

    # ── Persona CRUD ──────────────────────────────────────

    async def save_persona(self, persona: Persona):
        """保存人格（upsert by username）"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            await db.execute("""
                INSERT OR REPLACE INTO personas
                (username, tone, vocabulary, topics, style_metrics, updated_at, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                persona.username, persona.tone,
                persona.to_dict()['vocabulary'],
                persona.to_dict()['topics'],
                persona.to_dict()['style_metrics'],
                persona.updated_at.isoformat() if persona.updated_at else None,
                persona.source,
            ))
            await db.commit()
            logger.info(f"人格已保存: @{persona.username}")

    async def get_persona(self, username: str) -> Optional[Persona]:
        """获取指定用户的人格"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM personas WHERE username = ?",
                (username,)
            )
            row = await cursor.fetchone()
            if row:
                return Persona.from_dict(dict(row))
            return None

    async def get_latest_persona(self) -> Optional[Persona]:
        """获取最新的人格"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM personas ORDER BY updated_at DESC LIMIT 1"
            )
            row = await cursor.fetchone()
            if row:
                return Persona.from_dict(dict(row))
            return None

    async def get_all_personas(self) -> List[Persona]:
        """获取所有人格"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM personas ORDER BY updated_at DESC"
            )
            rows = await cursor.fetchall()
            return [Persona.from_dict(dict(row)) for row in rows]

    # ── PostHistory CRUD ──────────────────────────────────

    async def save_post(self, post: PostHistory) -> int:
        """保存发布记录，返回自增ID"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            cursor = await db.execute("""
                INSERT INTO post_history
                (content, image_path, posted_at, tweet_id, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                post.content,
                post.image_path,
                post.posted_at.isoformat() if post.posted_at else None,
                post.tweet_id,
                post.status,
                post.error_message,
            ))
            await db.commit()
            return cursor.lastrowid

    async def update_post_status(self, post_id: int, status: str,
                                 tweet_id: Optional[str] = None,
                                 error_message: Optional[str] = None):
        """更新发布状态"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            await db.execute("""
                UPDATE post_history
                SET status = ?, tweet_id = ?, error_message = ?
                WHERE id = ?
            """, (status, tweet_id, error_message, post_id))
            await db.commit()

    async def get_posts_today(self) -> int:
        """获取今日发布数量"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            cursor = await db.execute("""
                SELECT COUNT(*) FROM post_history
                WHERE status = 'success'
                AND date(posted_at) = date('now')
            """)
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_recent_posts(self, limit: int = 20) -> List[PostHistory]:
        """获取最近的发布记录"""
        async with aiosqlite.connect(str(self.db_path)) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM post_history
                ORDER BY posted_at DESC
                LIMIT ?
            """, (limit,))
            rows = await cursor.fetchall()
            return [PostHistory.from_dict(dict(row)) for row in rows]
