"""
数据模型定义
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
import json


@dataclass
class Tweet:
    """推文模型"""
    tweet_id: str
    username: str
    content: str
    created_at: Optional[datetime] = None
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    source: str = ""  # crawl / search

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat() if self.created_at else None
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Tweet':
        """从字典创建实例"""
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        return cls(
            tweet_id=data['tweet_id'],
            username=data['username'],
            content=data['content'],
            created_at=created_at,
            likes=data.get('likes', 0),
            retweets=data.get('retweets', 0),
            replies=data.get('replies', 0),
            source=data.get('source', ''),
        )


@dataclass
class Persona:
    """人格特征模型"""
    username: str
    tone: str = ""  # 语气风格
    vocabulary: list = None  # 高频词汇
    topics: list = None  # 话题偏好
    style_metrics: Dict[str, Any] = None  # 风格指标
    data_sources: list = None  # 外部数据源 (e.g. ["zhihu_hot", "zhihu_search: AI"])
    updated_at: Optional[datetime] = None
    source: str = "distilled"  # distilled / custom

    def __post_init__(self):
        if self.vocabulary is None:
            self.vocabulary = []
        if self.topics is None:
            self.topics = []
        if self.style_metrics is None:
            self.style_metrics = {}
        if self.data_sources is None:
            self.data_sources = []

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'username': self.username,
            'tone': self.tone,
            'vocabulary': json.dumps(self.vocabulary, ensure_ascii=False),
            'topics': json.dumps(self.topics, ensure_ascii=False),
            'style_metrics': json.dumps(self.style_metrics, ensure_ascii=False),
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'source': self.source,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Persona':
        """从字典创建实例"""
        return cls(
            username=data['username'],
            tone=data.get('tone', ''),
            vocabulary=json.loads(data.get('vocabulary', '[]')),
            topics=json.loads(data.get('topics', '[]')),
            style_metrics=json.loads(data.get('style_metrics', '{}')),
            updated_at=datetime.fromisoformat(data['updated_at']) if data.get('updated_at') else None,
            source=data.get('source', 'distilled'),
        )


@dataclass
class PostHistory:
    """发布历史模型"""
    id: Optional[int] = None
    content: str = ""
    image_path: Optional[str] = None
    posted_at: Optional[datetime] = None
    tweet_id: Optional[str] = None
    status: str = "pending"  # pending / success / failed
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        if self.posted_at:
            data['posted_at'] = self.posted_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PostHistory':
        """从字典创建实例"""
        posted_at = data.get('posted_at')
        if isinstance(posted_at, str):
            posted_at = datetime.fromisoformat(posted_at)
        return cls(
            id=data.get('id'),
            content=data.get('content', ''),
            image_path=data.get('image_path'),
            posted_at=posted_at,
            tweet_id=data.get('tweet_id'),
            status=data.get('status', 'pending'),
            error_message=data.get('error_message'),
        )
