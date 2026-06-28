"""
人格蒸馏模块
使用 Claude API 分析推文风格并提取人格特征
"""
import json
from typing import List, Dict, Any
from datetime import datetime
from loguru import logger
from anthropic import Anthropic

from ..config import config
from ..storage.models import Tweet, Persona
from ..storage.database import Database


class PersonaDistiller:
    """人格蒸馏器"""

    def __init__(self, db: Database):
        self.db = db

        # 初始化 Anthropic 客户端，支持代理和自定义 base_url
        client_kwargs: dict = {"api_key": config.anthropic_api_key}
        if config.anthropic_base_url:
            client_kwargs["base_url"] = config.anthropic_base_url
            logger.info(f"使用自定义 Anthropic API: {config.anthropic_base_url}")
        http_client = config.get_httpx_client()
        if http_client:
            client_kwargs["http_client"] = http_client
            logger.info(f"Anthropic 通过代理连接: {config.http_proxy}")

        self.client = Anthropic(**client_kwargs)

    async def analyze_user(self, username: str) -> Persona:
        """分析用户推文并生成人格特征"""
        # 从数据库获取推文
        tweets = await self.db.get_user_tweets(username, limit=200)

        if not tweets:
            raise ValueError(f"没有找到用户 @{username} 的推文数据")

        logger.info(f"开始分析 @{username} 的 {len(tweets)} 条推文")

        # 构建分析 prompt
        tweet_texts = [t.content for t in tweets]
        persona_data = await self._analyze_with_claude(username, tweet_texts)

        # 创建 Persona 对象
        persona = Persona(
            username=username,
            tone=persona_data.get('tone', ''),
            vocabulary=persona_data.get('vocabulary', []),
            topics=persona_data.get('topics', []),
            style_metrics=persona_data.get('style_metrics', {}),
            updated_at=datetime.now()
        )

        # 保存到数据库
        await self.db.save_persona(persona)

        logger.info(f"人格蒸馏完成: @{username}")
        return persona

    async def _analyze_with_claude(self, username: str, tweets: List[str]) -> Dict[str, Any]:
        """使用 Claude API 分析推文"""
        prompt = self._build_analysis_prompt(username, tweets)

        try:
            message = self.client.messages.create(
                model=config.anthropic_model,
                max_tokens=config.anthropic_max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            # 解析 JSON 响应
            response_text = message.content[0].text
            result = json.loads(response_text)

            logger.info(f"Claude 分析完成，提取了 {len(result.get('vocabulary', []))} 个高频词")
            return result

        except json.JSONDecodeError as e:
            logger.error(f"解析 Claude 响应失败: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"调用 Claude API 失败: {str(e)}")
            raise

    def _build_analysis_prompt(self, username: str, tweets: List[str]) -> str:
        """构建分析 prompt"""
        tweets_sample = tweets[:100]  # 限制推文数量以控制 token 使用
        tweets_text = "\n".join([f"- {t}" for t in tweets_sample])

        prompt = f"""
你是一个社交媒体人格分析专家。请分析用户 @{username} 的以下 {len(tweets_sample)} 条推文，提取其人格特征。

推文内容：
{tweets_text}

请以 JSON 格式返回分析结果（仅返回 JSON，不要其他文本）：

{{
  "tone": "描述用户的语气风格（例如：专业严谨、幽默风趣、随意亲切等）",
  "vocabulary": ["高频词汇1", "高频词汇2", "..."],
  "topics": ["主要话题1", "主要话题2", "..."],
  "style_metrics": {{
    "avg_length": 平均推文字数,
    "emoji_usage": "高/中/低",
    "formality": 正式度评分(0-10),
    "humor_level": 幽默度评分(0-10),
    "technical_depth": 技术深度评分(0-10)
  }}
}}

分析要求：
1. 准确捕捉用户的表达习惯和高频词汇
2. 识别用户关注的主要话题领域（最多5个）
3. 评估语言风格的正式度、幽默感和技术含量
4. 注意特殊的表达方式、口头禅、emoji 使用习惯
"""

        return prompt
