"""
X/Twitter API 客户端
使用 X 官方 XDK Python SDK + OAuth 1.0a 认证
"""
from typing import Optional, List, Dict, Any
from pathlib import Path
from loguru import logger
from xdk import Client as XdkClient
from xdk.oauth1_auth import OAuth1
from xdk.posts.models import (
    CreateRequest, CreateRequestMedia, CreateRequestReply,
)
from xdk.media.models import (
    InitializeUploadRequest, AppendUploadRequest,
)

from ..config import config


def _unwrap(response) -> Optional[Dict[str, Any]]:
    """从 XDK Pydantic 响应中提取 data dict"""
    if response is None:
        return None
    if hasattr(response, 'data'):
        data = response.data
        # Pydantic 对象 → dict
        if hasattr(data, 'dict'):
            return data.dict()
        if hasattr(data, 'model_dump'):
            return data.model_dump()
        if isinstance(data, dict):
            return data
        # 普通对象 → vars
        return vars(data) if hasattr(data, '__dict__') else data
    if isinstance(response, dict):
        return response
    return None


class XClient:
    """X/Twitter 客户端 — XDK + OAuth 1.0a"""

    def __init__(self):
        # ── OAuth 1.0a (User Context: post/delete/like/search) ──
        if all([config.x_api_key, config.x_api_secret,
                 config.x_access_token, config.x_access_token_secret]):
            auth = OAuth1(
                api_key=config.x_api_key,
                api_secret=config.x_api_secret,
                callback="http://localhost:8080/callback",
                access_token=config.x_access_token,
                access_token_secret=config.x_access_token_secret,
            )
            self._client = XdkClient(auth=auth)
            logger.info("XDK OAuth 1.0a 客户端就绪")
        else:
            logger.warning(
                "X OAuth 1.0a 凭证不完整，发帖/搜索功能不可用。请在 .env 中配置:\n"
                "  X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET"
            )
            self._client = None

        # ── Bearer Token (App-Only: trends 等公开接口) ──
        if config.x_bearer_token:
            self._bearer = XdkClient(bearer_token=config.x_bearer_token)
            logger.info("XDK Bearer Token (App-Only) 就绪")
        else:
            self._bearer = None

        # ── OAuth 2.0 (PKCE, 部分 v2 接口) ──
        if config.x_client_id and config.x_client_secret:
            self._oauth2 = XdkClient(
                client_id=config.x_client_id,
                client_secret=config.x_client_secret,
                redirect_uri=config.x_redirect_uri,
            )
            logger.info("XDK OAuth 2.0 就绪")
        else:
            self._oauth2 = None

    @property
    def ready(self) -> bool:
        return self._client is not None

    def _require(self):
        if not self._client:
            raise RuntimeError("X 客户端未初始化，请检查 OAuth 1.0a 凭证")

    # ═══════════════════════════════════════════════════════════════
    # 推文
    # ═══════════════════════════════════════════════════════════════

    def post(self, text: str, media_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """发布推文"""
        self._require()
        if len(text) > 280:
            text = text[:277] + "..."

        media = CreateRequestMedia(media_ids=media_ids) if media_ids else None
        body = CreateRequest(text=text, media=media)

        logger.info(f"发布推文: {text[:60]}...")
        result = self._client.posts.create(body=body)
        data = _unwrap(result) or {}
        tweet_id = data.get('id', '')
        logger.success(f"推文发布成功! ID: {tweet_id}")
        return {"tweet_id": tweet_id, "data": data}

    def reply(self, tweet_id: str, text: str) -> Dict[str, Any]:
        self._require()
        body = CreateRequest(
            text=text,
            reply=CreateRequestReply(in_reply_to_tweet_id=tweet_id),
        )
        result = self._client.posts.create(body=body)
        return {"tweet_id": (_unwrap(result) or {}).get('id', '')}

    def quote(self, tweet_id: str, text: str) -> Dict[str, Any]:
        self._require()
        body = CreateRequest(text=text, quote_tweet_id=tweet_id)
        result = self._client.posts.create(body=body)
        return {"tweet_id": (_unwrap(result) or {}).get('id', '')}

    def delete(self, tweet_id: str) -> bool:
        self._require()
        try:
            self._client.posts.delete(tweet_id)
            return True
        except Exception as e:
            logger.error(f"删除失败: {e}")
            return False

    def like(self, tweet_id: str) -> bool:
        self._require()
        try:
            self._client.users.like_post(tweet_id)
            return True
        except Exception as e:
            logger.error(f"点赞失败: {e}")
            return False

    def repost(self, tweet_id: str) -> bool:
        self._require()
        try:
            self._client.users.repost_post(tweet_id)
            return True
        except Exception as e:
            logger.error(f"转推失败: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════
    # 媒体上传 (INIT → APPEND → FINALIZE)
    # ═══════════════════════════════════════════════════════════════

    def upload_media(self, file_path: str) -> Optional[str]:
        """上传媒体，返回 media_id"""
        self._require()
        path = Path(file_path)
        if not path.exists():
            logger.error(f"文件不存在: {file_path}")
            return None

        try:
            file_size = path.stat().st_size
            media_type = _guess_media_type(path.suffix)
            logger.info(f"上传媒体: {path.name} ({file_size} bytes, {media_type})")

            init = self._client.media.initialize_upload(body=InitializeUploadRequest(
                media_type=media_type,
                total_bytes=file_size,
            ))
            # XDK 返回 InitializeUploadResponse, .data.id 即 media_id
            media_id = getattr(getattr(init, 'data', None), 'id', None)
            if not media_id:
                logger.error("INIT 失败：未获取 media_id")
                return None

            import base64
            with open(path, 'rb') as f:
                self._client.media.append_upload(
                    media_id, body=AppendUploadRequest(
                        media=base64.b64encode(f.read()).decode(),
                        segment_index=0,
                    ))

            self._client.media.finalize_upload(media_id)
            logger.success(f"媒体上传成功: media_id={media_id}")
            return media_id
        except Exception as e:
            logger.error(f"媒体上传失败: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════
    # 搜索
    # ═══════════════════════════════════════════════════════════════

    def search(self, query: str, count: int = 10,
               recent: bool = True) -> List[Dict[str, Any]]:
        self._require()
        logger.info(f"搜索: '{query}', count={count}")
        try:
            fn = self._client.posts.search_recent if recent else self._client.posts.search_all
            result = fn(query=query, max_results=count)
            data = _unwrap(result)
            posts = data.get('data', data) if isinstance(data, dict) else data
            return posts if isinstance(posts, list) else []
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return []

    def search_user(self, username: str, count: int = 50) -> List[Dict[str, Any]]:
        return self.search(f"from:{username}", count=count)

    # ═══════════════════════════════════════════════════════════════
    # 社交图谱
    # ═══════════════════════════════════════════════════════════════

    def following(self, count: int = 50) -> List[Dict[str, Any]]:
        """获取关注列表 (需要用户 ID, 不是 'me')"""
        self._require()
        try:
            # 先获取自己的用户 ID
            me = self.whoami()
            user_id = me.get('id', '') if me else None
            if not user_id:
                logger.error("无法获取自己的用户 ID")
                return []

            results = []
            for page in self._client.users.get_following(
                    user_id, max_results=min(count, 100)):
                data = _unwrap(page)
                users = data.get('data', data) if isinstance(data, dict) else data
                if isinstance(users, list):
                    results.extend(users)
                    if len(results) >= count:
                        break
            logger.info(f"关注列表: {len(results)} 个用户")
            return results[:count]
        except Exception as e:
            logger.error(f"获取关注列表失败: {e}")
            return []

    def timeline_users(self, count: int = 50) -> List[str]:
        """从时间线推文中提取活跃用户"""
        tweets = self.timeline(count=count)
        users = set()
        for t in tweets:
            author = t.get('author_id') or t.get('author', {}).get('username', '')
            if author:
                users.add(author)
        return list(users)

    # ═══════════════════════════════════════════════════════════════
    # 用户
    # ═══════════════════════════════════════════════════════════════

    def timeline(self, count: int = 20) -> List[Dict[str, Any]]:
        self._require()
        try:
            results = []
            for page in self._client.users.get_timeline(
                    "me", max_results=min(count, 100)):
                data = _unwrap(page)
                posts = data.get('data', data) if isinstance(data, dict) else data
                if isinstance(posts, list):
                    results.extend(posts)
                    if len(results) >= count:
                        break
            return results[:count]
        except Exception as e:
            logger.error(f"获取时间线失败: {e}")
            return []

    def user_posts(self, user_id: str, count: int = 50) -> List[Dict[str, Any]]:
        self._require()
        try:
            result = self._client.users.get_posts(user_id, max_results=count)
            data = _unwrap(result)
            posts = data.get('data', data) if isinstance(data, dict) else data
            return posts if isinstance(posts, list) else []
        except Exception as e:
            logger.error(f"获取用户推文失败: {e}")
            return []

    def whoami(self) -> Optional[Dict[str, Any]]:
        self._require()
        try:
            return _unwrap(self._client.users.get_me())
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return None

    def user_info(self, username: str) -> Optional[Dict[str, Any]]:
        self._require()
        try:
            return _unwrap(self._client.users.get_by_username(username))
        except Exception as e:
            logger.error(f"获取 @{username} 失败: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════
    # 趋势
    # ═══════════════════════════════════════════════════════════════

    # 常见 WOEID
    WOEID = {
        "worldwide": 1,
        "us": 23424977,
        "uk": 23424975,
        "japan": 23424856,
        "korea": 23424868,
        "canada": 23424775,
    }

    def trends(self, woeid: int = 1, max_trends: int = 20) -> List[Dict[str, Any]]:
        """获取地区趋势 (App-Only Bearer Token)
        WOEID: 1=全球, 23424977=美国, 23424856=日本 等
        """
        if not self._bearer:
            logger.error("趋势接口需要 Bearer Token，请在 .env 中配置 X_BEARER_TOKEN")
            return []
        logger.info(f"获取趋势: WOEID={woeid}")
        try:
            result = self._bearer.trends.get_by_woeid(
                woeid=woeid, max_trends=max_trends)
            data = _unwrap(result)
            trends = data.get('data', data) if isinstance(data, dict) else data
            return trends if isinstance(trends, list) else []
        except Exception as e:
            logger.error(f"获取趋势失败: {e}")
            return []

    def personalized_trends(self) -> List[Dict[str, Any]]:
        """获取个性化趋势（需要 OAuth 1.0a User Context）"""
        self._require()
        logger.info("获取个性化趋势...")
        try:
            result = self._client.trends.get_personalized()
            data = _unwrap(result)
            trends = data.get('data', data) if isinstance(data, dict) else data
            return trends if isinstance(trends, list) else []
        except Exception as e:
            logger.error(f"获取个性化趋势失败: {e}")
            return []


def _guess_media_type(suffix: str) -> str:
    return {
        '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.gif': 'image/gif', '.webp': 'image/webp', '.mp4': 'video/mp4',
    }.get(suffix.lower(), 'image/png')
