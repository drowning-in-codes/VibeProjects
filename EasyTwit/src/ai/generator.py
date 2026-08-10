"""
内容生成模块
基于人格特征使用 Claude API 生成推文
"""
from typing import Optional, Tuple, List
from loguru import logger
from anthropic import Anthropic

from ..config import config
from ..storage.models import Persona, Tweet
from ..storage.database import Database
from .image import ImageManager


class ContentGenerator:
    """推文内容生成器"""

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

        # 图片管理器
        self.image_manager = ImageManager() if config.image_enabled else None

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
        return Anthropic(**client_kwargs)

    def should_generate_image(self, tweet_content: str) -> bool:
        """智能判断推文是否需要配图"""
        if not config.image_enabled:
            return False

        # 太短的推文不需要图片
        if len(tweet_content) < 40:
            return False

        # 适合配图的推文类型
        image_friendly_keywords = [
            "AI", "GPT", "Claude", "技术", "科技", "代码", "编程",
            "产品", "发布", "上线", "推出", "新功能", "更新",
            "教程", "指南", "如何", "方法", "步骤", "技巧",
            "设计", "界面", "UI", "UX", "图表", "数据", "趋势",
            "未来", "世界", "城市", "空间", "场景",
        ]

        if any(keyword in tweet_content for keyword in image_friendly_keywords):
            return True

        # 不适合配图的推文类型
        text_only_keywords = [
            "早安", "晚安", "早上好", "晚上好", "周末愉快",
            "我认为", "个人观点", "想法分享",
            "感谢", "谢谢", "欢迎", "恭喜",
        ]

        if any(keyword in tweet_content for keyword in text_only_keywords):
            return False

        # 包含具体描述 -> 更适合配图
        descriptive_words = ["展示", "呈现", "看到", "观察", "发现", "效果"]
        if any(word in tweet_content for word in descriptive_words):
            return True

        # 默认：长推文配图
        return len(tweet_content) > 80

    async def generate_tweet(
        self,
        persona: Optional[Persona] = None,
        topic: Optional[str] = None,
        with_image: Optional[bool] = None,
        reference_tweets: Optional[List[Tweet]] = None,
    ) -> Tuple[str, Optional[str]]:
        """生成符合人格风格的推文（返回文本和图片路径）

        Args:
            persona: 人格特征（None 则使用数据库中最新的）
            topic: 话题关键词（可选）
            with_image: 是否生成图片
                - True: 强制生成图片
                - False: 强制不生成图片
                - None: 自动判断
            reference_tweets: 参考推文列表（用于保持风格一致性）

        Returns:
            (推文内容, 图片路径) — 图片路径可能为 None
        """
        if persona is None:
            persona = await self.db.get_latest_persona()
            if persona is None:
                raise ValueError("没有可用的人格数据，请先创建人格")

        logger.info(f"开始生成推文，基于 @{persona.username} 的人格特征")

        # 加载外部数据源 (知乎), 失败或无结果则兜底使用人格信息
        external_context = ""
        if persona.data_sources:
            try:
                from ..zhihu.client import ZhihuClient
                zhihu = ZhihuClient()
                if zhihu.ready:
                    external_context = zhihu.fetch_context(
                        persona.data_sources, query=topic, limit=5)
                    if external_context:
                        logger.info(f"  ✓ 知乎数据源已加载 ({len(external_context)} 字符)")
                    else:
                        logger.info("  → 知乎未返回有效数据，使用人格信息兜底")
                else:
                    logger.info("  → 知乎未配置 Access Secret，使用人格信息兜底")
            except Exception as e:
                logger.warning(f"  → 知乎数据源异常 ({e})，使用人格信息兜底")

        prompt = self._build_generation_prompt(persona, topic, reference_tweets,
                                               external_context=external_context)
        max_retries = config.get('anthropic.generation_retries', 3)

        try:
            from .fallback import try_with_fallback

            def call(client):
                kwargs = dict(
                    model=config.anthropic_model,
                    max_tokens=500,
                    messages=[{"role": "user", "content": prompt}],
                )
                system = config.get('anthropic.system_prompt', '')
                if system:
                    kwargs["system"] = system
                message = client.messages.create(**kwargs)
                return self._extract_text(message).strip()

            tweet_content = ""
            for attempt in range(1, max_retries + 1):
                tweet_content = await try_with_fallback(
                    primary_fn=lambda: call(self.client),
                    backup_fn=lambda: call(self.backup_client) if self.backup_client else None,
                    label="Claude",
                )
                if tweet_content and len(tweet_content) >= 10:
                    break
                logger.warning(
                    f"生成结果为空或过短 ({len(tweet_content)} 字符), "
                    f"重试 {attempt}/{max_retries}..."
                )

            if not tweet_content or len(tweet_content) < 10:
                raise ValueError(f"经过 {max_retries} 次重试仍无法生成有效推文")

            # 去掉可能的引号包裹
            if (tweet_content.startswith('"') and tweet_content.endswith('"')) or \
               (tweet_content.startswith("'") and tweet_content.endswith("'")):
                tweet_content = tweet_content[1:-1]

            logger.info(f"推文生成成功 ({len(tweet_content)} 字符): {tweet_content[:60]}...")
            if len(tweet_content) > 280:
                logger.info(f"内容超过 280 字符，将以推文串 (thread) 形式发布")

            # 智能判断是否需要配图
            if with_image is None:
                with_image = self.should_generate_image(tweet_content)
                if with_image:
                    logger.info("智能判断：该推文适合配图")
                else:
                    logger.info("智能判断：该推文不需要配图")

            # 生成图片
            image_path = None
            if with_image and self.image_manager:
                image_path = await self.image_manager.get_image_for_tweet(
                    tweet_content, topic
                )

            return tweet_content, image_path

        except Exception as e:
            logger.error(f"生成推文失败: {e}")
            raise

    def _build_generation_prompt(
        self,
        persona: Persona,
        topic: Optional[str],
        reference_tweets: Optional[List[Tweet]] = None,
        external_context: str = "",
    ) -> str:
        """构建生成 prompt"""
        vocabulary_str = "、".join(persona.vocabulary[:15])
        topics_str = "、".join(persona.topics)

        style_metrics = persona.style_metrics
        formality = style_metrics.get('formality', 5)
        humor = style_metrics.get('humor_level', 5)

        # 加载外部 prompt 模板
        template = self._load_prompt_template()
        parts = []
        if template:
            parts.append(template + "\n")

        parts.append(f"""
你需要完全模仿 @{persona.username} 的推文风格来创作一条新推文。

人格特征：
- 语气风格: {persona.tone}
- 常用词汇: {vocabulary_str}
- 关注话题: {topics_str}
- 正式度: {formality}/10
- 幽默感: {humor}/10
- Emoji 使用: {style_metrics.get('emoji_usage', '中')}
- 平均长度: {style_metrics.get('avg_length', 100)} 字符
""")

        # 添加参考推文
        if reference_tweets:
            ref_texts = "\n".join([
                f"- {t.content}" for t in reference_tweets[:5]
            ])
            parts.append(f"""
参考推文（请模仿其风格）：
{ref_texts}
""")

        # 外部数据源 (知乎等)
        if external_context:
            parts.append(f"""
以下是当前外部平台的热点内容和讨论，请从中获取灵感并结合人格风格创作推文。
不要直接复制，但可以参考热点话题和观点视角：
{external_context}
""")

        # 话题要求
        if topic:
            parts.append(f"话题要求: {topic}")
        else:
            parts.append(f"请自由选择一个符合该用户兴趣的话题（如: {topics_str}）")

        parts.append("""
创作要求：
1. 严格遵循上述人格特征和风格
2. 使用该用户的常用词汇和表达方式
3. 保持语气、幽默感和正式度一致
4. 长度控制在 260-500 字符之间 (内容要有深度, 超出 280 会自动拆成推文串)
5. 如果该用户常用 emoji，请自然地使用
6. 内容要有价值，不要空洞无物
7. 推文要像真人发的，不要像广告或机器人
8. 直接返回推文内容，不要任何解释或引号

请生成推文：
""")

        return "".join(parts)

    @staticmethod
    def _load_prompt_template() -> str:
        """从外部 .md 文件加载 prompt 模板"""
        from pathlib import Path
        template_path = config.prompt_template
        if not template_path:
            return ""
        path = Path(template_path)
        if path.exists():
            return path.read_text(encoding='utf-8')
        logger.warning(f"模板文件不存在: {template_path}")
        return ""

    @staticmethod
    def _extract_text(message) -> str:
        """从 Anthropic 响应中提取文本（兼容 ThinkingBlock）"""
        for block in message.content:
            if hasattr(block, 'text'):
                return block.text
            if hasattr(block, 'thinking'):
                continue
        return ""

    @staticmethod
    def split_thread(text: str, max_len: int = 270) -> list[str]:
        """将长文本按句子边界拆分为推文串

        每段 ≤ max_len，优先在句号/换行处断开，保留完整语义。
        """
        if len(text) <= max_len:
            return [text]

        # 按句子分割点拆分
        import re
        sentences = re.split(r'(?<=[。！？\.\!\?\n])\s*', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        current = ""
        for s in sentences:
            if len(current) + len(s) + 1 <= max_len:
                current = (current + " " + s).strip() if current else s
            else:
                if current:
                    chunks.append(current)
                # 如果单句也太长，强制切开
                if len(s) > max_len:
                    for i in range(0, len(s), max_len - 3):
                        chunks.append(s[i:i + max_len - 3] + "...")
                else:
                    current = s
        if current:
            chunks.append(current)

        # 添加序号标记: "1/n text"
        n = len(chunks)
        if n > 1:
            chunks = [f"{i+1}/{n} {c}" for i, c in enumerate(chunks)]

        return chunks
