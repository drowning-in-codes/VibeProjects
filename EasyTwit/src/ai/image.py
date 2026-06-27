"""
AI 图片生成模块
Primary: nanobanana (Gemini API)
Backup:  GPT-Image-2 (Chat Completions API)
图片生成失败时只记录日志，不阻断推文发布流程
"""
import json
import httpx
from pathlib import Path
from typing import Optional
from loguru import logger
from openai import OpenAI

from ..config import config


class ImageManager:
    """图片管理器 — nanobanana 模型族(主) + GPT-Image-2(备) + 本地缓存"""

    def __init__(self):
        self.output_dir = Path(config.image_output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # ── nanobanana (Primary) ──
        self.nanobanana_key = config.nanobanana_api_key
        self.nanobanana_base = self._strip_api_version(config.nanobanana_base_url)
        self.nanobanana_model = config.nanobanana_model
        self._nanobanana_ok = bool(self.nanobanana_key)

        # ── GPT-Image-2 (Backup) ──
        self.openai_client = self._make_openai_client(
            config.openai_api_key,
            config.openai_base_url,
        )
        self.gpt_image_model = config.get('openai.model', 'gpt-image-2')

        # 日志
        if self._nanobanana_ok:
            logger.info(f"图片管理器: nanobanana ({self.nanobanana_model}) + GPT-Image-2 备用")
        elif self.openai_client:
            logger.info(f"图片管理器: GPT-Image-2 ({self.gpt_image_model}) — nanobanana 未配置")
        else:
            logger.warning("未配置任何图片 API Key，图片生成不可用")

    @staticmethod
    def _strip_api_version(url: str) -> str:
        """去掉 base URL 中末尾的 /v1 等版本号（Gemini 端点自带 v1beta）"""
        import re
        return re.sub(r'/v\d+$', '', url)

    @staticmethod
    def _make_openai_client(api_key: Optional[str], base_url: Optional[str] = None) -> Optional[OpenAI]:
        if not api_key:
            return None
        kw: dict = {"api_key": api_key}
        if base_url:
            kw["base_url"] = base_url
        return OpenAI(**kw)

    # ═══════════════════════════════════════════════════════════════
    # 主入口
    # ═══════════════════════════════════════════════════════════════

    async def get_image_for_tweet(self, tweet_content: str,
                                  topic: Optional[str] = None) -> Optional[str]:
        """为推文生成配图

        Returns: 图片文件路径，失败返回 None（不阻断发帖）
        """
        prompt = self._build_image_prompt(tweet_content, topic)

        # 1. 尝试 nanobanana
        if self._nanobanana_ok:
            image_path = await self._try_nanobanana(prompt)
            if image_path:
                return image_path
            logger.info("nanobanana 失败，切换到 GPT-Image-2...")

        # 2. 尝试 GPT-Image-2 (backup)
        if self.openai_client:
            image_path = await self._try_gpt_image(prompt)
            if image_path:
                return image_path

        # 3. 全部失败 → 降级纯文本
        logger.warning("⚠️ 图片生成失败，将以纯文本方式发布推文（不影响推文发送）")
        return None

    # ═══════════════════════════════════════════════════════════════
    # nanobanana 模型族
    # ═══════════════════════════════════════════════════════════════

    async def _try_nanobanana(self, prompt: str) -> Optional[str]:
        """nanobanana 图片生成"""
        url = (
            f"{self.nanobanana_base}/v1beta/models/"
            f"{self.nanobanana_model}:generateContent"
            f"?key={self.nanobanana_key}"
        )

        body = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(url, json=body)
                resp.raise_for_status()
                data = resp.json()

            image_data = self._parse_gemini_response(data)
            if not image_data:
                logger.warning("nanobanana 响应中未找到图片数据")
                return None

            image_path = self._save_base64_image(
                image_data.get('data', ''),
                image_data.get('mime', 'image/png'),
            )
            if image_path:
                logger.info(f"nanobanana 图片生成成功 → {image_path}")
            return image_path

        except Exception as e:
            logger.warning(f"nanobanana 调用失败: {e}")
            return None

    @staticmethod
    def _parse_gemini_response(data: dict) -> Optional[dict]:
        """解析 Gemini API 响应，提取图片数据"""
        try:
            candidates = data.get('candidates', [])
            if not candidates:
                return None

            parts = candidates[0].get('content', {}).get('parts', [])
            for part in parts:
                inline = part.get('inlineData')
                if inline and inline.get('data'):
                    return {
                        'data': inline['data'],
                        'mime': inline.get('mimeType', 'image/png'),
                    }
                text = part.get('text', '')
                if text:
                    import re
                    md = re.search(r'!\[.*?\]\((https?://[^\s\)]+)\)', text)
                    if md:
                        return {'data': md.group(1), 'mime': 'url', 'is_url': True}
            return None
        except Exception:
            return None

    # ═══════════════════════════════════════════════════════════════
    # GPT-Image-2 — Chat Completions (Backup)
    # ═══════════════════════════════════════════════════════════════

    async def _try_gpt_image(self, prompt: str) -> Optional[str]:
        """GPT-Image-2 图片生成"""
        try:
            completion = self.openai_client.chat.completions.create(
                model=self.gpt_image_model,
                messages=[{"role": "user", "content": prompt}],
            )
            content = completion.choices[0].message.content
            if not content:
                return None

            image_url = self._extract_url_from_text(content)
            if image_url:
                image_path = await self._download_image(image_url)
                if image_path:
                    logger.info(f"GPT-Image-2 图片生成成功")
                return image_path
            return None

        except Exception as e:
            logger.warning(f"GPT-Image-2 调用失败: {e}")
            return None

    @staticmethod
    def _extract_url_from_text(content: str) -> Optional[str]:
        """从文本中提取图片 URL"""
        import re
        m = re.search(r'!\[.*?\]\((https?://[^\s\)]+)\)', content)
        if m:
            return m.group(1)
        m = re.search(r'(https?://[^\s]+\.(?:png|jpg|jpeg|gif|webp)[^\s]*)', content, re.IGNORECASE)
        if m:
            return m.group(1)
        if content.startswith('http'):
            return content.strip()
        return None

    # ═══════════════════════════════════════════════════════════════
    # 工具方法
    # ═══════════════════════════════════════════════════════════════

    def _save_base64_image(self, data: str, mime: str = 'image/png') -> Optional[str]:
        """保存 base64 或 URL 图片到本地"""
        import base64
        import hashlib
        import asyncio

        if mime == 'url':
            return asyncio.run(self._download_image(data))

        try:
            raw = base64.b64decode(data)
        except Exception as e:
            logger.warning(f"base64 解码失败: {e}")
            return None

        ext = mime.split('/')[-1] if '/' in mime else 'png'
        if ext == 'jpeg':
            ext = 'jpg'

        file_hash = hashlib.md5(raw[:100]).hexdigest()[:12]
        filename = f"img_{file_hash}.{ext}"
        filepath = self.output_dir / filename
        filepath.write_bytes(raw)
        return str(filepath)

    async def _download_image(self, url: str) -> Optional[str]:
        """下载图片到本地"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(url)
                resp.raise_for_status()

                import hashlib
                file_hash = hashlib.md5(url.encode()).hexdigest()[:12]
                filename = f"img_{file_hash}.png"
                filepath = self.output_dir / filename
                filepath.write_bytes(resp.content)
                return str(filepath)

        except Exception as e:
            logger.warning(f"下载图片失败: {e}")
            return None

    def _build_image_prompt(self, tweet_content: str,
                            topic: Optional[str] = None) -> str:
        """根据推文内容构建图片生成提示词"""
        base = topic or tweet_content[:100]
        return f"""A visually stunning and modern illustration representing: {base}

Style requirements:
- Clean, minimalist design with high visual impact
- Professional color palette, no text in the image
- Suitable for a tech/social media audience
- Abstract or semi-abstract style, avoiding realistic faces
- High contrast, visually appealing at small sizes (social media thumbnail)
- NOT photorealistic, artistic and stylized"""

    def get_image_path(self, filename: str) -> str:
        return str(self.output_dir / filename)

    def list_images(self) -> list:
        if not self.output_dir.exists():
            return []
        return [str(p) for p in self.output_dir.glob("*.png")]

    def cleanup_old_images(self, days: int = 30):
        import time
        if not self.output_dir.exists():
            return
        cutoff = time.time() - days * 86400
        for p in self.output_dir.glob("*.png"):
            if p.stat().st_mtime < cutoff:
                p.unlink()
                logger.info(f"删除旧图片: {p.name}")
