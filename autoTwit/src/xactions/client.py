"""
XActions 客户端封装
通过 Node.js 调用 XActions npm 包
"""
import json
import asyncio
import subprocess
from typing import List, Dict, Any, Optional
from pathlib import Path
from loguru import logger

from ..config import config


class XActionsClient:
    """XActions 客户端"""

    def __init__(self):
        self.auth_token = config.x_auth_token
        self.node_script_path = Path(__file__).parent / "xactions_wrapper.js"

    async def _run_node_script(self, tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """运行 Node.js 脚本调用 XActions"""
        script_data = {
            'tool': tool,
            'params': params,
            'authToken': self.auth_token
        }

        try:
            # 调用 Node.js 脚本
            process = await asyncio.create_subprocess_exec(
                'node',
                str(self.node_script_path),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate(
                json.dumps(script_data).encode()
            )

            if process.returncode != 0:
                error_msg = stderr.decode()
                logger.error(f"XActions 调用失败: {error_msg}")
                raise Exception(f"XActions error: {error_msg}")

            result = json.loads(stdout.decode())
            return result

        except Exception as e:
            logger.error(f"执行 XActions 工具 {tool} 失败: {str(e)}")
            raise

    async def scrape_user_tweets(self, username: str, count: int = 100) -> List[Dict[str, Any]]:
        """爬取用户推文"""
        logger.info(f"开始爬取 @{username} 的推文，数量: {count}")

        result = await self._run_node_script('scrape_user_tweets', {
            'username': username,
            'count': count
        })

        tweets = result.get('tweets', [])
        logger.info(f"成功爬取 {len(tweets)} 条推文")
        return tweets

    async def get_user_profile(self, username: str) -> Dict[str, Any]:
        """获取用户信息"""
        logger.info(f"获取 @{username} 的用户信息")

        result = await self._run_node_script('get_user_profile', {
            'username': username
        })

        return result.get('profile', {})

    async def post_tweet(self, content: str, image_path: Optional[str] = None) -> Dict[str, Any]:
        """发布推文（支持图片）"""
        logger.info(f"发布推文: {content[:50]}...")

        params = {'text': content}
        if image_path:
            params['image_path'] = image_path
            logger.info(f"附带图片: {image_path}")

        result = await self._run_node_script('post_tweet', params)

        logger.info(f"推文发布成功，ID: {result.get('tweet_id')}")
        return result

    async def like_tweet(self, tweet_id: str) -> bool:
        """点赞推文"""
        logger.info(f"点赞推文: {tweet_id}")

        result = await self._run_node_script('like_tweet', {
            'tweet_id': tweet_id
        })

        return result.get('success', False)

    async def follow_user(self, username: str) -> bool:
        """关注用户"""
        logger.info(f"关注用户: @{username}")

        result = await self._run_node_script('follow_user', {
            'username': username
        })

        return result.get('success', False)

    async def search_tweets(self, query: str, count: int = 50) -> List[Dict[str, Any]]:
        """搜索推文"""
        logger.info(f"搜索推文: {query}")

        result = await self._run_node_script('search_tweets', {
            'query': query,
            'count': count
        })

        return result.get('tweets', [])
