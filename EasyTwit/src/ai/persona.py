"""
人格蒸馏与自定义生成模块
使用 Claude API 分析推文风格并提取人格特征，支持自定义关键词/描述生成人格
"""
import json
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
from anthropic import Anthropic

from ..config import config
from ..storage.models import Tweet, Persona
from ..storage.database import Database


class PersonaManager:
    """人格管理器 — 蒸馏分析 + 自定义生成"""

    def __init__(self, db: Database):
        self.db = db

        http_client = config.get_httpx_client()

        # 主 Anthropic 客户端
        self.client = self._make_client(
            config.anthropic_api_key,
            config.anthropic_base_url,
            http_client,
        )

        # 备用 Anthropic 客户端
        self.backup_client = None
        if config.anthropic_backup_api_key:
            self.backup_client = self._make_client(
                config.anthropic_backup_api_key,
                config.anthropic_backup_base_url,
                http_client,
            )
            logger.info(f"已配置备用 Anthropic API: {config.anthropic_backup_base_url or 'default'}")

    @staticmethod
    def _make_client(api_key: str, base_url: Optional[str] = None,
                     http_client=None) -> Optional[Anthropic]:
        """创建 Anthropic 客户端实例"""
        client_kwargs: dict = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
            logger.info(f"Anthropic endpoint: {base_url}")
        if http_client:
            client_kwargs["http_client"] = http_client
            logger.info(f"Anthropic 通过代理连接: {config.http_proxy}")
        return Anthropic(**client_kwargs)

    # ═══════════════════════════════════════════════════════════════
    # 人格蒸馏（从推文分析）
    # ═══════════════════════════════════════════════════════════════

    async def distill_from_tweets(self, username: str,
                                  tweets: Optional[List[Tweet]] = None,
                                  limit: int = 200) -> Persona:
        """从推文蒸馏人格特征

        Args:
            username: X 用户名
            tweets: 推文列表（为 None 则从数据库获取）
            limit: 从数据库获取的最大数量

        Returns:
            人格特征对象
        """
        # 获取推文
        if tweets is None:
            tweets = await self.db.get_user_tweets(username, limit=limit)

        if not tweets:
            raise ValueError(f"没有找到 @{username} 的推文数据，请先爬取")

        logger.info(f"开始分析 @{username} 的 {len(tweets)} 条推文")

        # 构建分析 prompt
        tweet_texts = [t.content for t in tweets]
        persona_data = await self._analyze_with_claude(username, tweet_texts)

        # 创建 Persona
        persona = Persona(
            username=username,
            tone=persona_data.get('tone', ''),
            vocabulary=persona_data.get('vocabulary', []),
            topics=persona_data.get('topics', []),
            style_metrics=persona_data.get('style_metrics', {}),
            updated_at=datetime.now(),
            source='distilled',
        )

        # 保存到数据库
        await self.db.save_persona(persona)

        # 回写到 personas/ 目录
        self._save_persona_yaml(persona)

        logger.info(f"人格蒸馏完成: @{username}")
        return persona

    # ═══════════════════════════════════════════════════════════════
    # 自定义人格（关键词/描述生成）
    # ═══════════════════════════════════════════════════════════════

    async def create_custom_persona(self, name: str, description: str,
                                    keywords: List[str], tone: str = "",
                                    topics: Optional[List[str]] = None) -> Persona:
        """根据描述和关键词创建自定义人格

        Args:
            name: 人格名称（如 "技术博主"）
            description: 人格描述
            keywords: 关键词列表
            tone: 语气风格
            topics: 话题列表

        Returns:
            人格特征对象
        """
        logger.info(f"创建自定义人格: '{name}'")

        prompt = f"""
你需要根据用户提供的信息，生成一个完整的社交媒体人格画像。

人物描述: {description}
关键词: {', '.join(keywords)}
{"语气风格: " + tone if tone else ""}
{"关注话题: " + ', '.join(topics) if topics else ""}

请以 JSON 格式返回（仅返回 JSON）：

{{
  "tone": "语气风格概述（50字以内）",
  "vocabulary": ["高频词1", "高频词2", "...（15-20个）"],
  "topics": ["话题1", "话题2", "...（最多5个）"],
  "style_metrics": {{
    "avg_length": 平均推文长度估算（50-200之间）,
    "emoji_usage": "高/中/低/无",
    "formality": 正式度评分(0-10),
    "humor_level": 幽默度评分(0-10),
    "technical_depth": 技术深度评分(0-10)
  }},
  "quintessence": "用一段话（80-120字）概括这个角色的表达精髓"
}}

要求：
1. 人格特征要具体、可模仿
2. 高频词汇要有代表性
3. 风格指标要合理一致
4. 确保生成的角色有鲜明的表达风格
"""

        persona_data = await self._call_claude(prompt)
        persona_data['quintessence'] = persona_data.get('quintessence', description)

        persona = Persona(
            username=name.replace(' ', '_').lower(),
            tone=persona_data.get('tone', tone),
            vocabulary=persona_data.get('vocabulary', keywords[:15]),
            topics=persona_data.get('topics', topics or []),
            style_metrics=persona_data.get('style_metrics', {}),
            updated_at=datetime.now(),
            source='custom',
        )

        await self.db.save_persona(persona)
        logger.info(f"自定义人格已创建: '{name}'")
        return persona

    def _save_persona_yaml(self, persona: Persona):
        """将蒸馏后的人格保存为 personas/{username}.yaml 模板"""
        tmpl_dir = Path("personas")
        tmpl_dir.mkdir(parents=True, exist_ok=True)
        path = tmpl_dir / f"{persona.username}.yaml"

        data = {
            "name": persona.username,
            "description": persona.tone,
            "keywords": persona.vocabulary[:15] if persona.vocabulary else [],
            "tone": persona.tone,
            "topics": persona.topics if persona.topics else [],
        }

        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        logger.info(f"人格模板已保存: {path}")

    async def create_persona_from_template(self) -> Optional[Persona]:
        """从 personas/ 目录加载 YAML 模板，用 AI 生成人格

        template 为空或 "random" → 随机选一个
        template = "tech-blogger" → 加载 personas/tech-blogger.yaml
        """
        import random as _random
        template_name = config.persona_template

        # 空或 random → 随机选
        if not template_name or template_name == "random":
            tmpl_dir = Path("personas")
            if not tmpl_dir.exists():
                logger.error("personas/ 目录不存在")
                return None
            files = list(tmpl_dir.glob("*.yaml"))
            if not files:
                logger.error("personas/ 目录无模板文件")
                return None
            path = _random.choice(files)
            template_name = path.stem
        else:
            path = Path(f"personas/{template_name}.yaml")
            if not path.exists():
                logger.error(f"人格模板文件不存在: {path}")
                return None

        cfg = yaml.safe_load(path.read_text(encoding='utf-8'))
        name = cfg.get('name', template_name)

        logger.info(f"从模板创建人格: {name} ({path})")
        return await self.create_custom_persona(
            name=name,
            description=cfg.get('description', ''),
            keywords=cfg.get('keywords', []),
            tone=cfg.get('tone', ''),
            topics=cfg.get('topics'),
        )

    async def create_persona_from_config(self) -> Optional[Persona]:
        """兼容旧接口，实际调用 create_persona_from_template"""
        return await self.create_persona_from_template()

    # ═══════════════════════════════════════════════════════════════
    # 内部方法
    # ═══════════════════════════════════════════════════════════════

    async def _analyze_with_claude(self, username: str,
                                   tweets: List[str]) -> Dict[str, Any]:
        """使用 Claude API 分析推文（带主备切换）"""
        prompt = self._build_analysis_prompt(username, tweets)

        def call(client):
            message = client.messages.create(
                model=config.anthropic_model,
                max_tokens=config.anthropic_max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            response_text = self._extract_text(message)
            result = self._parse_json_safe(response_text)
            logger.info(
                f"Claude 分析完成，提取了 {len(result.get('vocabulary', []))} 个高频词"
            )
            return result

        from .fallback import try_with_fallback
        return await try_with_fallback(
            primary_fn=lambda: call(self.client),
            backup_fn=lambda: call(self.backup_client) if self.backup_client else None,
            label="Claude",
        )

    async def _call_claude(self, prompt: str) -> Dict[str, Any]:
        """调用 Claude API（带主备切换）"""
        def call(client):
            message = client.messages.create(
                model=config.anthropic_model,
                max_tokens=config.anthropic_max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return self._parse_json_safe(self._extract_text(message))

        from .fallback import try_with_fallback
        return await try_with_fallback(
            primary_fn=lambda: call(self.client),
            backup_fn=lambda: call(self.backup_client) if self.backup_client else None,
            label="Claude",
        )

    def _build_analysis_prompt(self, username: str,
                               tweets: List[str]) -> str:
        """构建推文分析 prompt"""
        # 限制样本量控制 token
        tweets_sample = tweets[:100]
        tweets_text = "\n".join([f"- {t}" for t in tweets_sample])

        return f"""你是一个社交媒体人格分析专家。请分析用户 @{username} 的以下 {len(tweets_sample)} 条推文，提取其人格特征。

推文内容：
{tweets_text}

请以 JSON 格式返回分析结果（仅返回 JSON，不要其他文本）：

{{
  "tone": "描述用户的语气风格（例如：专业严谨、幽默风趣、随意亲切等）",
  "vocabulary": ["高频词汇1", "高频词汇2", "..."],
  "topics": ["主要话题1", "主要话题2", "..."],
  "style_metrics": {{
    "avg_length": 平均推文字数,
    "emoji_usage": "高/中/低/无",
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
5. 推文可能包含 #hashtag、@mention、链接等元素，请用原始推文内容分析
"""

    @staticmethod
    def _extract_text(message) -> str:
        """从 Anthropic 响应中提取文本（兼容 ThinkingBlock）"""
        for block in message.content:
            if hasattr(block, 'text'):
                return block.text
            if hasattr(block, 'thinking'):
                continue  # 跳过 thinking block
        return ""

    @staticmethod
    def _parse_json_safe(text: str) -> Dict[str, Any]:
        """安全的 JSON 解析"""
        import re
        text = text.strip()
        # 去掉可能的 ```json 包裹
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 尝试提取 JSON 对象
            m = re.search(r"\{[\s\S]*\}", text)
            if m:
                return json.loads(m.group())
            raise
