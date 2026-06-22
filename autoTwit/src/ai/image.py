"""
图片生成和获取模块
支持从多个来源获取或生成图片
"""
import os
import httpx
from pathlib import Path
from typing import Optional
from loguru import logger
from openai import OpenAI

from .image_prompt_optimizer import ImagePromptOptimizer


class ImageProvider:
    """图片提供者基类"""

    async def get_image(self, prompt: str, topic: str) -> Optional[str]:
        """获取图片路径"""
        raise NotImplementedError


class LocalImageProvider(ImageProvider):
    """本地图片库"""

    def __init__(self, image_dir: str = "./images"):
        self.image_dir = Path(image_dir)
        self.image_dir.mkdir(exist_ok=True)

    async def get_image(self, prompt: str, topic: str) -> Optional[str]:
        """从本地图片库选择图片"""
        # 根据主题查找图片
        topic_lower = topic.lower() if topic else ""

        for image_file in self.image_dir.glob("*.*"):
            if image_file.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                # 简单的关键词匹配
                if topic_lower in image_file.stem.lower():
                    logger.info(f"找到本地图片: {image_file}")
                    return str(image_file)

        return None


class UnsplashProvider(ImageProvider):
    """Unsplash 免费图片"""

    def __init__(self, access_key: Optional[str] = None):
        self.access_key = access_key or os.getenv("UNSPLASH_ACCESS_KEY")
        self.base_url = "https://api.unsplash.com"

    async def get_image(self, prompt: str, topic: str) -> Optional[str]:
        """从 Unsplash 搜索并下载图片"""
        if not self.access_key:
            logger.warning("未配置 UNSPLASH_ACCESS_KEY，跳过")
            return None

        try:
            query = topic or prompt[:50]

            async with httpx.AsyncClient() as client:
                # 搜索图片
                response = await client.get(
                    f"{self.base_url}/search/photos",
                    params={"query": query, "per_page": 1},
                    headers={"Authorization": f"Client-ID {self.access_key}"}
                )

                if response.status_code != 200:
                    logger.error(f"Unsplash 搜索失败: {response.status_code}")
                    return None

                data = response.json()
                results = data.get("results", [])

                if not results:
                    logger.warning(f"未找到相关图片: {query}")
                    return None

                # 下载图片
                image_url = results[0]["urls"]["regular"]
                image_id = results[0]["id"]

                image_path = Path(f"./temp/{image_id}.jpg")
                image_path.parent.mkdir(exist_ok=True)

                image_response = await client.get(image_url)
                image_path.write_bytes(image_response.content)

                logger.info(f"从 Unsplash 下载图片: {image_path}")
                return str(image_path)

        except Exception as e:
            logger.error(f"Unsplash 获取图片失败: {str(e)}")
            return None


class DALLEProvider(ImageProvider):
    """DALL-E 图片生成（支持 DALL-E 2 和 DALL-E 3）"""

    def __init__(self, api_key: Optional[str] = None, model: str = "dall-e-3"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if self.api_key:
            # 初始化 OpenAI 客户端，支持自定义 base_url
            client_kwargs = {"api_key": self.api_key}
            base_url = os.getenv("OPENAI_BASE_URL")
            if base_url:
                client_kwargs["base_url"] = base_url
                logger.info(f"使用自定义 OpenAI API: {base_url}")

            self.client = OpenAI(**client_kwargs)
        else:
            self.client = None
        self.optimizer = ImagePromptOptimizer()
        self.model = model  # "dall-e-2" or "dall-e-3"

    async def get_image(self, prompt: str, topic: str) -> Optional[str]:
        """使用 DALL-E 生成图片 - 根据推文内容智能生成"""
        if not self.client:
            logger.warning("未配置 OPENAI_API_KEY，跳过 DALL-E")
            return None

        try:
            # 第 1 步：使用 Claude 分析推文，提取视觉元素
            logger.info("正在分析推文内容，提取视觉元素...")
            visual_elements = await self.optimizer.analyze_tweet_for_image(prompt)

            # 第 2 步：构建优化后的 DALL-E prompt
            image_prompt = self.optimizer.build_dalle_prompt(visual_elements)

            logger.info(f"使用 {self.model.upper()} 生成图片...")
            logger.debug(f"Prompt: {image_prompt[:100]}...")

            # DALL-E 2 和 DALL-E 3 参数不同
            if self.model == "dall-e-2":
                response = self.client.images.generate(
                    model="dall-e-2",
                    prompt=image_prompt[:1000],  # DALL-E 2 限制 1000 字符
                    size="512x512",  # DALL-E 2 支持 256x256, 512x512, 1024x1024
                    n=1,
                )
            else:  # dall-e-3
                response = self.client.images.generate(
                    model="dall-e-3",
                    prompt=image_prompt,
                    size="1024x1024",
                    quality="standard",
                    n=1,
                )

            image_url = response.data[0].url

            # 下载图片
            async with httpx.AsyncClient() as client:
                image_response = await client.get(image_url)

                image_path = Path(f"./temp/{self.model}_{hash(prompt)}.png")
                image_path.parent.mkdir(exist_ok=True)
                image_path.write_bytes(image_response.content)

                logger.info(f"{self.model.upper()} 图片生成完成: {image_path}")
                return str(image_path)

        except Exception as e:
            logger.error(f"DALL-E 生成图片失败: {str(e)}")
            return None

    def _build_image_prompt(self, tweet_content: str, topic: str) -> str:
        """构建 DALL-E prompt - 根据推文内容生成图片"""
        return f"""
基于以下推文内容，创建一张高质量的配图：

推文内容：{tweet_content}

要求：
- 视觉风格：现代、简洁、专业
- 适合社交媒体发布
- 不要在图片中包含任何文字
- 颜色搭配和谐
- 与推文主题高度相关
"""


class ImageManager:
    """图片管理器 - 统一接口"""

    def __init__(self, dalle_model: str = "dall-e-3"):
        """
        初始化图片管理器

        Args:
            dalle_model: "dall-e-2" 或 "dall-e-3"
        """
        self.providers = [
            LocalImageProvider(),
            UnsplashProvider(),
            DALLEProvider(model=dalle_model)
        ]
        self.dalle_model = dalle_model

    async def get_image_for_tweet(self, tweet_content: str, topic: Optional[str] = None) -> Optional[str]:
        """为推文获取合适的图片"""
        logger.info("开始为推文获取图片")

        # 按优先级尝试各个提供者
        for provider in self.providers:
            try:
                image_path = await provider.get_image(tweet_content, topic or "")
                if image_path:
                    logger.info(f"成功获取图片: {image_path}")
                    return image_path
            except Exception as e:
                logger.error(f"{provider.__class__.__name__} 失败: {str(e)}")
                continue

        logger.warning("未能获取图片，将发布纯文本推文")
        return None
