"""
数据库操作类
使用 SQLite 存储数据
"""
import aiosqlite
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from loguru import logger

from .models import User, Tweet, Persona, ZhihuContent, PostHistory


class Database:
    """数据库操作类"""

    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def init_db(self):
        """初始化数据库表"""
        async with aiosqlite.connect(self.db_path) as db:
            # 用户表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    display_name TEXT,
                    bio TEXT,
                    followers_count INTEGER DEFAULT 0,
                    following_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP
                )
            """)

            # 推文表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tweets (
                    tweet_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    likes INTEGER DEFAULT 0,
                    retweets INTEGER DEFAULT 0,
                    replies INTEGER DEFAULT 0,
                    FOREIGN KEY (username) REFERENCES users(username)
                )
            """)

            # 创建索引
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_tweets_username
                ON tweets(username)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_tweets_created_at
                ON tweets(created_at DESC)
            """)

            # 人格特征表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS personas (
                    username TEXT PRIMARY KEY,
                    tone TEXT NOT NULL,
                    vocabulary TEXT NOT NULL,
                    topics TEXT NOT NULL,
                    style_metrics TEXT NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (username) REFERENCES users(username)
                )
            """)

            # 知乎内容表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS zhihu_contents (
                    content_id TEXT PRIMARY KEY,
                    content_type TEXT NOT NULL,
                    title TEXT,
                    content TEXT NOT NULL,
                    author_name TEXT,
                    author_id TEXT,
                    vote_count INTEGER DEFAULT 0,
                    comment_count INTEGER DEFAULT 0,
                    created_at TEXT,
                    url TEXT,
                    author_avatar TEXT,
                    author_badge TEXT,
                    author_badge_text TEXT,
                    authority_level INTEGER DEFAULT 0,
                    source TEXT DEFAULT 'zhihu_search',
                    edit_time INTEGER,
                    collected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 兼容旧表：尝试添加新列
            for col in [
                "url TEXT", "author_avatar TEXT", "author_badge TEXT",
                "author_badge_text TEXT", "authority_level INTEGER DEFAULT 0",
                "source TEXT DEFAULT 'zhihu_search'", "edit_time INTEGER"
            ]:
                try:
                    await db.execute(f"ALTER TABLE zhihu_contents ADD COLUMN {col}")
                except Exception:
                    pass  # 列已存在

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_zhihu_author
                ON zhihu_contents(author_id)
            """)

            # 发布历史表
            await db.execute("""
                CREATE TABLE IF NOT EXISTS post_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    posted_at TIMESTAMP,
                    tweet_id TEXT,
                    status TEXT DEFAULT 'pending'
                )
            """)

            await db.commit()
            logger.info(f"数据库初始化完成: {self.db_path}")

    async def save_user(self, user: User):
        """保存用户信息"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO users
                (username, display_name, bio, followers_count, following_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user.username,
                user.display_name,
                user.bio,
                user.followers_count,
                user.following_count,
                user.created_at
            ))
            await db.commit()

    async def save_tweets(self, tweets: List[Tweet]):
        """批量保存推文"""
        async with aiosqlite.connect(self.db_path) as db:
            for tweet in tweets:
                await db.execute("""
                    INSERT OR REPLACE INTO tweets
                    (tweet_id, username, content, created_at, likes, retweets, replies)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    tweet.tweet_id,
                    tweet.username,
                    tweet.content,
                    tweet.created_at,
                    tweet.likes,
                    tweet.retweets,
                    tweet.replies
                ))
            await db.commit()
            logger.info(f"保存了 {len(tweets)} 条推文")

    async def get_user_tweets(self, username: str, limit: int = 100) -> List[Tweet]:
        """获取用户推文"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM tweets
                WHERE username = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (username, limit)) as cursor:
                rows = await cursor.fetchall()
                return [
                    Tweet(
                        tweet_id=row['tweet_id'],
                        username=row['username'],
                        content=row['content'],
                        created_at=datetime.fromisoformat(row['created_at']),
                        likes=row['likes'],
                        retweets=row['retweets'],
                        replies=row['replies']
                    )
                    for row in rows
                ]

    async def save_persona(self, persona: Persona):
        """保存人格特征"""
        async with aiosqlite.connect(self.db_path) as db:
            data = persona.to_dict()
            await db.execute("""
                INSERT OR REPLACE INTO personas
                (username, tone, vocabulary, topics, style_metrics, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                data['username'],
                data['tone'],
                data['vocabulary'],
                data['topics'],
                data['style_metrics'],
                data['updated_at']
            ))
            await db.commit()
            logger.info(f"保存了用户 {persona.username} 的人格特征")

    async def get_persona(self, username: str) -> Optional[Persona]:
        """获取人格特征"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM personas WHERE username = ?
            """, (username,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Persona.from_dict(dict(row))
                return None

    async def get_latest_persona(self) -> Optional[Persona]:
        """获取最新的人格特征"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM personas
                ORDER BY updated_at DESC
                LIMIT 1
            """) as cursor:
                row = await cursor.fetchone()
                if row:
                    return Persona.from_dict(dict(row))
                return None

    async def save_zhihu_contents(self, contents: List[ZhihuContent]):
        """批量保存知乎内容"""
        async with aiosqlite.connect(self.db_path) as db:
            for c in contents:
                await db.execute("""
                    INSERT OR REPLACE INTO zhihu_contents
                    (content_id, content_type, title, content, author_name,
                     author_id, vote_count, comment_count, created_at,
                     url, author_avatar, author_badge, author_badge_text,
                     authority_level, source, edit_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    c.content_id, c.content_type, c.title, c.content,
                    c.author_name, c.author_id, c.vote_count,
                    c.comment_count, c.created_at,
                    c.url, c.author_avatar, c.author_badge, c.author_badge_text,
                    c.authority_level, c.source, c.edit_time
                ))
            await db.commit()
            logger.info(f"保存了 {len(contents)} 条知乎内容")

    def _row_to_zhihu_content(self, row: dict) -> ZhihuContent:
        """将数据库行转为 ZhihuContent，兼容新旧字段"""
        return ZhihuContent(
            content_id=row['content_id'],
            content_type=row['content_type'],
            title=row['title'],
            content=row['content'],
            author_name=row['author_name'],
            author_id=row['author_id'],
            vote_count=row['vote_count'],
            comment_count=row['comment_count'],
            created_at=row['created_at'],
            url=row['url'] if 'url' in row.keys() else None,
            author_avatar=row['author_avatar'] if 'author_avatar' in row.keys() else None,
            author_badge=row['author_badge'] if 'author_badge' in row.keys() else None,
            author_badge_text=row['author_badge_text'] if 'author_badge_text' in row.keys() else None,
            authority_level=row['authority_level'] if 'authority_level' in row.keys() else 0,
            source=row['source'] if 'source' in row.keys() else 'zhihu_search',
            edit_time=row['edit_time'] if 'edit_time' in row.keys() else None,
        )

    async def get_zhihu_contents_by_author(self, author_id: str, limit: int = 50) -> List[ZhihuContent]:
        """获取指定作者的知乎内容"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM zhihu_contents
                WHERE author_id = ?
                ORDER BY vote_count DESC
                LIMIT ?
            """, (author_id, limit)) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_zhihu_content(dict(row)) for row in rows]

    async def get_latest_zhihu_contents(self, limit: int = 50) -> List[ZhihuContent]:
        """获取最新的知乎内容"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM zhihu_contents
                ORDER BY collected_at DESC
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [self._row_to_zhihu_content(dict(row)) for row in rows]

    async def save_post_history(self, content: str, tweet_id: Optional[str] = None,
                                 status: str = "success"):
        """保存发布历史"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO post_history (content, posted_at, tweet_id, status)
                VALUES (?, ?, ?, ?)
            """, (content, datetime.now(), tweet_id, status))
            await db.commit()

    async def get_post_history(self, limit: int = 50) -> List[PostHistory]:
        """获取发布历史"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT * FROM post_history
                ORDER BY posted_at DESC
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
                return [
                    PostHistory(
                        id=row['id'],
                        content=row['content'],
                        posted_at=datetime.fromisoformat(row['posted_at']) if row['posted_at'] else None,
                        tweet_id=row['tweet_id'],
                        status=row['status']
                    )
                    for row in rows
                ]
