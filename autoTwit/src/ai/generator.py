"""
内容生成模块
基于人格特征使用 Claude API 生成推文
"""
from typing import Optional, Tuple
from loguru import logger
from anthropic import Anthropic

from ..config import config
from ..storage.models import Persona
from ..storage.database import Database
from .image import ImageManager


class ContentGenerator:
    """内容生成器"""

    def __init__(self, db: Database):
        self.db = db

        # 初始化 Anthropic 客户端，支持自定义 base_url
        client_kwargs = {"api_key": config.anthropic_api_key}
        if config.anthropic_base_url:
            client_kwargs["base_url"] = config.anthropic_base_url
            logger.info(f"使用自定义 Anthropic API: {config.anthropic_base_url}")

        self.client = Anthropic(**client_kwargs)
        dalle_model = config.get('image.dalle.model', 'dall-e-3')
        self.image_manager = ImageManager(dalle_model=dalle_model)

    def should_generate_image(self, tweet_content: str) -> bool:
        """智能判断推文是否需要配图"""

        # 1. 太短的推文不需要图片（简短问候等）
        if len(tweet_content) < 40:
            return False

        # 2. 适合配图的推文类型
        image_friendly_keywords = [
            # 科技类
            "AI", "人工智能", "GPT", "Claude", "技术", "科技", "代码", "编程",
            # 产品类
            "产品", "发布", "上线", "推出", "新功能", "更新",
            # 教程类
            "教程", "指南", "如何", "方法", "步骤", "技巧",
            # 视觉化内容
            "设计", "界面", "UI", "UX", "图表", "数据", "趋势",
            # 场景描述
            "未来", "世界", "城市", "空间", "场景"
        ]

        if any(keyword in tweet_content for keyword in image_friendly_keywords):
            return True

        # 3. 不适合配图的推文类型
        text_only_keywords = [
            # 简单问候
            "早安", "晚安", "早上好", "晚上好", "周末愉快",
            # 纯观点
            "我认为", "个人观点", "想法分享",
            # 简单互动
            "感谢", "谢谢", "欢迎", "恭喜"
        ]

        if any(keyword in tweet_content for keyword in text_only_keywords):
            return False

        # 4. 检查是否包含具体描述（更可能需要配图）
        descriptive_words = ["展示", "呈现", "看到", "观察", "发现", "效果"]
        if any(word in tweet_content for word in descriptive_words):
            return True

        # 5. 默认：长推文配图，短推文不配
        return len(tweet_content) > 80

    async def generate_tweet(self, persona: Optional[Persona] = None,
                            topic: Optional[str] = None,
                            with_image: Optional[bool] = None) -> Tuple[str, Optional[str]]:
        """生成符合人格风格的推文（返回文本和图片路径）

        Args:
            persona: 人格特征（None 则使用数据库中最新的）
            topic: 话题关键词（可选）
            with_image: 是否生成图片
                - True: 强制生成图片
                - False: 强制不生成图片
                - None: 自动判断（根据推文内容智能决定）
        """
        # 如果没有提供 persona，从数据库获取最新的
        if persona is None:
            persona = await self.db.get_latest_persona()
            if persona is None:
                raise ValueError("没有可用的人格数据，请先进行人格蒸馏")

        logger.info(f"开始生成推文，基于用户 @{persona.username} 的人格特征")

        prompt = self._build_generation_prompt(persona, topic)

        try:
            message = self.client.messages.create(
                model=config.anthropic_model,
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            tweet_content = message.content[0].text.strip()

            # 确保推文长度不超过 280 字符
            if len(tweet_content) > 280:
                logger.warning(f"生成的推文超过 280 字符，进行截断")
                tweet_content = tweet_content[:277] + "..."

            logger.info(f"推文生成成功: {tweet_content[:50]}...")

            # 智能判断是否需要配图
            if with_image is None:
                # 自动判断模式
                with_image = self.should_generate_image(tweet_content)
                if with_image:
                    logger.info("智能判断：该推文适合配图")
                else:
                    logger.info("智能判断：该推文不需要配图")
            elif with_image:
                logger.info("强制生成配图模式")
            else:
                logger.info("强制无图模式")

            # 获取图片（如果需要）
            image_path = None
            if with_image:
                image_path = await self.image_manager.get_image_for_tweet(tweet_content, topic)

            return tweet_content, image_path

        except Exception as e:
            logger.error(f"生成推文失败: {str(e)}")
            raise

    def _build_generation_prompt(self, persona: Persona, topic: Optional[str]) -> str:
        """构建生成 prompt"""
        vocabulary_str = "、".join(persona.vocabulary[:15])
        topics_str = "、".join(persona.topics)

        style_metrics = persona.style_metrics
        formality = style_metrics.get('formality', 5)
        humor = style_metrics.get('humor_level', 5)

        prompt = f"""
你需要完全模仿 @{persona.username} 的推文风格来创作一条新推文。

人格特征：
- 语气风格: {persona.tone}
- 常用词汇: {vocabulary_str}
- 关注话题: {topics_str}
- 正式度: {formality}/10
- 幽默感: {humor}/10
- Emoji 使用: {style_metrics.get('emoji_usage', '中')}
- 平均长度: {style_metrics.get('avg_length', 100)} 字符

{"话题要求: " + topic if topic else "请自由选择一个符合该用户兴趣的话题"}

创作要求：
1. 严格遵循上述人格特征和风格
2. 使用该用户的常用词汇和表达方式
3. 保持语气、幽默感和正式度一致
4. 长度控制在 50-280 字符之间
5. 如果该用户常用 emoji，请自然地使用
6. 内容要有价值，不要空洞无物
7. 直接返回推文内容，不要任何解释或引号

请生成推文：
"""

        return prompt
