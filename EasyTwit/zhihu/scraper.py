"""
知乎内容爬取器
使用知乎开放平台 API 搜索并收集内容
"""
from typing import List, Optional, Set
from loguru import logger

from .client import ZhihuAPIClient
from ..storage.database import Database
from ..storage.models import ZhihuContent


class ZhihuScraper:
    """知乎内容爬取器"""

    def __init__(self, db: Database, client: ZhihuAPIClient):
        self.db = db
        self.client = client

    async def search_and_collect(
        self, query: str, limit: int = 50
    ) -> List[ZhihuContent]:
        """
        搜索并收集知乎内容

        Args:
            query: 搜索关键词
            limit: 最大返回数量

        Returns:
            收集到的知乎内容列表
        """
        logger.info(f"开始搜索知乎: query='{query}', limit={limit}")

        raw_items = self.client.search_all(query, max_results=limit)

        if not raw_items:
            logger.warning(f"搜索 '{query}' 无结果")
            return []

        contents = self._parse_items(raw_items)
        unique = self._deduplicate(contents)

        if unique:
            await self.db.save_zhihu_contents(unique)
            logger.info(f"保存了 {len(unique)} 条知乎内容")

        return unique

    async def collect_by_author(
        self, author_name: str, limit: int = 50
    ) -> List[ZhihuContent]:
        """
        通过搜索作者名收集其内容

        Args:
            author_name: 作者名称
            limit: 最大数量

        Returns:
            该作者的内容列表
        """
        # 搜索作者名 → 获取相关回答/文章
        raw_items = self.client.search_all(author_name, max_results=limit)

        if not raw_items:
            return []

        contents = self._parse_items(raw_items)

        # 过滤只保留该作者的内容
        author_contents = [
            c
            for c in contents
            if c.author_name and author_name.lower() in c.author_name.lower()
        ]

        if author_contents:
            await self.db.save_zhihu_contents(author_contents)

        return author_contents

    async def global_search_and_collect(
        self,
        query: str,
        limit: int = 40,
        filter_expr: Optional[str] = None,
        search_db: str = "all",
    ) -> List[ZhihuContent]:
        """
        全网搜索并收集内容

        Args:
            query: 搜索关键词
            limit: 最大数量
            filter_expr: 高级语法筛选
            search_db: 索引库选择

        Returns:
            收集到的知乎内容列表
        """
        logger.info(f"开始全网搜索: query='{query}', limit={limit}")

        raw_items = self.client.global_search_all(
            query, max_results=limit, filter_expr=filter_expr, search_db=search_db
        )

        if not raw_items:
            logger.warning(f"全网搜索 '{query}' 无结果")
            return []

        contents = self._parse_global_items(raw_items)
        unique = self._deduplicate(contents)

        if unique:
            await self.db.save_zhihu_contents(unique)
            logger.info(f"全网搜索保存了 {len(unique)} 条内容")

        return unique

    # ── 解析 ──────────────────────────────────────────────

    def _parse_items(self, items: List[dict]) -> List[ZhihuContent]:
        """解析 API 返回的原始数据项"""
        contents: List[ZhihuContent] = []

        for item in items:
            try:
                # 知乎搜索 API 返回的字段根据实际文档调整
                # 常见字段: id, type, title, content/excerpt, author, voteup_count 等
                content_type = item.get("type", "answer")
                content_id = str(item.get("id", ""))

                # 内容主体
                body = (
                    item.get("content")
                    or item.get("excerpt")
                    or item.get("summary")
                    or ""
                )

                # 标题（回答取问题标题，文章取文章标题）
                title = item.get("title", "")
                if not title:
                    question = item.get("question", {})
                    if isinstance(question, dict):
                        title = question.get("title", "")

                # 作者
                author = item.get("author", {})
                if isinstance(author, dict):
                    author_name = author.get("name", "")
                    author_id = author.get("url_token", "") or author.get("id", "")
                else:
                    author_name = ""
                    author_id = ""

                # 互动数据
                vote_count = item.get("voteup_count", 0) or item.get("like_count", 0)
                comment_count = item.get("comment_count", 0)

                # 时间
                created_at = str(
                    item.get("created_time")
                    or item.get("created")
                    or item.get("updated_time", "")
                )

                if content_id and body:
                    contents.append(
                        ZhihuContent(
                            content_id=content_id,
                            content_type=content_type,
                            title=title,
                            content=body,
                            author_name=author_name,
                            author_id=author_id,
                            vote_count=vote_count,
                            comment_count=comment_count,
                            created_at=created_at,
                        )
                    )

            except Exception as e:
                logger.warning(f"解析知乎数据项失败: {str(e)}")
                continue

        return contents

    def _parse_global_items(self, items: List[dict]) -> List[ZhihuContent]:
        """解析全网搜索 (global_search) 响应格式

        Item 字段:
          Title, ContentType, ContentID, ContentText, Url,
          CommentCount, VoteUpCount, AuthorName, AuthorAvatar,
          AuthorBadge, AuthorBadgeText, EditTime, AuthorityLevel
        """
        contents: List[ZhihuContent] = []

        for item in items:
            try:
                content_id = str(item.get("ContentID", ""))
                body = item.get("ContentText", "")

                if not content_id or not body:
                    continue

                contents.append(
                    ZhihuContent(
                        content_id=content_id,
                        content_type=item.get("ContentType", "answer"),
                        title=item.get("Title", ""),
                        content=body,
                        author_name=item.get("AuthorName", ""),
                        author_id="",  # global_search 不返回 author_id
                        vote_count=item.get("VoteUpCount", 0),
                        comment_count=item.get("CommentCount", 0),
                        created_at=str(item.get("EditTime", "")),
                        url=item.get("Url", ""),
                        author_avatar=item.get("AuthorAvatar", ""),
                        author_badge=item.get("AuthorBadge", ""),
                        author_badge_text=item.get("AuthorBadgeText", ""),
                        authority_level=item.get("AuthorityLevel", 0),
                        source="global_search",
                        edit_time=item.get("EditTime"),
                    )
                )

            except Exception as e:
                logger.warning(f"解析全网搜索结果项失败: {str(e)}")
                continue

        return contents

    def _deduplicate(self, contents: List[ZhihuContent]) -> List[ZhihuContent]:
        """按 content_id 去重"""
        seen: Set[str] = set()
        unique: List[ZhihuContent] = []
        for c in contents:
            if c.content_id not in seen:
                seen.add(c.content_id)
                unique.append(c)
        return unique
