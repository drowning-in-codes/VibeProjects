"""
数据模型定义
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
import json


@dataclass
class User:
    """用户模型"""
    username: str
    display_name: Optional[str] = None
    bio: Optional[str] = None
    followers_count: Optional[int] = 0
    following_count: Optional[int] = 0
    created_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class Tweet:
    """推文模型"""
    tweet_id: str
    username: str
    content: str
    created_at: datetime
    likes: int = 0
    retweets: int = 0
    replies: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        return data


@dataclass
class Persona:
    """人格特征模型"""
    username: str
    tone: str  # 语气风格
    vocabulary: list  # 高频词汇
    topics: list  # 话题偏好
    style_metrics: Dict[str, Any]  # 风格指标
    updated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'username': self.username,
            'tone': self.tone,
            'vocabulary': json.dumps(self.vocabulary, ensure_ascii=False),
            'topics': json.dumps(self.topics, ensure_ascii=False),
            'style_metrics': json.dumps(self.style_metrics, ensure_ascii=False),
            'updated_at': self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Persona':
        """从字典创建实例"""
        return cls(
            username=data['username'],
            tone=data['tone'],
            vocabulary=json.loads(data['vocabulary']),
            topics=json.loads(data['topics']),
            style_metrics=json.loads(data['style_metrics']),
            updated_at=datetime.fromisoformat(data['updated_at'])
        )


@dataclass
class ZhihuContent:
    """知乎内容模型（兼容 zhihu_search 和 global_search 两种响应）"""
    content_id: str
    content_type: str  # answer / article
    title: Optional[str] = None
    content: str = ""
    author_name: Optional[str] = None
    author_id: Optional[str] = None
    vote_count: int = 0
    comment_count: int = 0
    created_at: Optional[str] = None
    # ── global_search 额外字段 ──
    url: Optional[str] = None
    author_avatar: Optional[str] = None
    author_badge: Optional[str] = None
    author_badge_text: Optional[str] = None
    authority_level: int = 0  # 1=低权威, 2=中权威, 3=高权威, 4=超高权威
    source: str = "zhihu_search"  # zhihu_search / global_search
    edit_time: Optional[int] = None  # 最后编辑时间戳（秒）

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


@dataclass
class PostHistory:
    """发布历史模型"""
    id: Optional[int] = None
    content: str = ""
    posted_at: Optional[datetime] = None
    tweet_id: Optional[str] = None
    status: str = "pending"  # pending/success/failed

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        if self.posted_at:
            data['posted_at'] = self.posted_at.isoformat()
        return data
