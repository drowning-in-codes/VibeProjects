"""
推文图片生成优化器
使用 Claude 分析推文内容，提取视觉元素，生成精准的图片生成 prompt
"""
import json
from typing import Dict, Any
from loguru import logger
from anthropic import Anthropic

from ..config import config


class ImagePromptOptimizer:
    """图片 Prompt 优化器"""

    def __init__(self):
        # 初始化 Anthropic 客户端，支持自定义 base_url
        from ..config import config

        client_kwargs = {"api_key": config.anthropic_api_key}
        if config.anthropic_base_url:
            client_kwargs["base_url"] = config.anthropic_base_url

        self.client = Anthropic(**client_kwargs)

    async def analyze_tweet_for_image(self, tweet_content: str) -> Dict[str, Any]:
        """分析推文内容，提取视觉元素"""
        prompt = f"""
分析以下推文，提取适合生成配图的视觉元素：

推文内容：
{tweet_content}

请以 JSON 格式返回（仅返回 JSON，不要其他文本）：

{{
  "main_subject": "主要视觉主体（如：宇航员、城市天际线、电路板等）",
  "scene": "场景描述（如：太空中、日落时分、科技实验室等）",
  "style": "视觉风格（如：科幻未来感、温暖写实、极简扁平等）",
  "mood": "情绪氛围（如：振奋人心、平静专注、活力充沛等）",
  "colors": ["主要配色1", "主要配色2"],
  "elements": ["关键元素1", "关键元素2", "关键元素3"],
  "avoid": ["避免的元素1", "避免的元素2"]
}}

分析要求：
1. 主体要具体可视觉化，避免抽象概念
2. 场景要清晰明确
3. 风格要适合社交媒体
4. 不要在图片中包含文字
"""

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-6",  # 使用 Sonnet 降低成本
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text
            visual_elements = json.loads(response_text)

            logger.info(f"视觉元素提取完成: {visual_elements['main_subject']}")
            return visual_elements

        except Exception as e:
            logger.error(f"分析推文失败: {str(e)}")
            # 返回默认值
            return {
                "main_subject": "abstract concept",
                "scene": "modern minimalist background",
                "style": "clean and professional",
                "mood": "inspiring",
                "colors": ["blue", "white"],
                "elements": [],
                "avoid": ["text", "words"]
            }

    def build_dalle_prompt(self, visual_elements: Dict[str, Any]) -> str:
        """根据视觉元素构建 DALL-E prompt"""
        elements_str = ", ".join(visual_elements.get("elements", []))
        avoid_str = ", ".join(visual_elements.get("avoid", []))
        colors_str = " and ".join(visual_elements.get("colors", []))

        prompt = f"""
A high-quality digital illustration for social media:

Main subject: {visual_elements['main_subject']}
Scene: {visual_elements['scene']}
Style: {visual_elements['style']}
Mood: {visual_elements['mood']}
Color palette: {colors_str}
Additional elements: {elements_str}

Requirements:
- Professional and polished
- Suitable for Twitter/X post
- No text or words in the image
- 16:9 or square aspect ratio
{f"- Avoid: {avoid_str}" if avoid_str else ""}
"""

        logger.info(f"DALL-E Prompt 构建完成")
        return prompt.strip()

    def build_midjourney_prompt(self, visual_elements: Dict[str, Any]) -> str:
        """根据视觉元素构建 Midjourney 风格 prompt"""
        elements = [
            visual_elements['main_subject'],
            visual_elements['scene'],
            visual_elements['style'],
            visual_elements['mood']
        ]

        elements.extend(visual_elements.get('elements', []))

        # Midjourney 参数
        params = [
            "--ar 16:9",
            "--style raw",
            "--v 6"
        ]

        prompt = ", ".join([e for e in elements if e]) + " " + " ".join(params)

        logger.info(f"Midjourney Prompt 构建完成")
        return prompt

    def build_stable_diffusion_prompt(self, visual_elements: Dict[str, Any]) -> str:
        """根据视觉元素构建 Stable Diffusion prompt"""
        positive_elements = [
            visual_elements['main_subject'],
            visual_elements['scene'],
            visual_elements['style'],
            "high quality",
            "detailed",
            "professional photography"
        ]

        positive_elements.extend(visual_elements.get('elements', []))
        positive_prompt = ", ".join([e for e in positive_elements if e])

        negative_elements = [
            "text", "words", "letters", "watermark",
            "low quality", "blurry", "distorted"
        ]
        negative_elements.extend(visual_elements.get('avoid', []))
        negative_prompt = ", ".join([e for e in negative_elements if e])

        logger.info(f"Stable Diffusion Prompt 构建完成")
        return f"Positive: {positive_prompt}\nNegative: {negative_prompt}"
