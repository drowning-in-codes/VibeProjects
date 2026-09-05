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


def _redact(text: str, secrets) -> str:
    """将字符串中的敏感信息替换为 ***，避免写入日志。

    1. 打码已知的 API key 值
    2. 打码 URL 中 key=... 查询参数 (可能 key 未知)
    3. 打码 Authorization: Bearer ... 头
    """
    import re
    for s in secrets:
        if s and s in text:
            text = text.replace(s, "***")
    # key=xxx 查询参数 (直至 & 或空白或引号)
    text = re.sub(r'(key=)[^&\s\'"]+', r'\1***', text)
    # Bearer token
    text = re.sub(r'(Bearer\s+)[A-Za-z0-9._\-]+', r'\1***', text)
    return text


class ImageManager:
    """图片管理器 — nanobanana 模型族(主) + GPT-Image-2(备) + 本地缓存"""

    def __init__(self):
        self.output_dir = Path(config.image_output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # ── 生图提供商 (按优先级从高到低) ──
        self.providers = config.image_providers
        self.gemini_key = config.gemini_api_key
        self.openai_key = config.openai_api_key

        # 日志: 列出可用的提供商
        available = []
        for p in self.providers:
            key = self.gemini_key if p.get('type', 'gemini') == 'gemini' else self.openai_key
            if key:
                available.append(f"{p.get('type')}:{p.get('model')}")
        if available:
            logger.info(f"图片管理器 ({len(available)} 个提供商): {', '.join(available)}")
        else:
            logger.warning("未配置任何图片 API Key，图片生成不可用")

    @staticmethod
    def _strip_api_version(url: str) -> str:
        """去掉 base URL 中末尾的 /v1 等版本号（Gemini 端点自带 v1beta）"""
        import re
        return re.sub(r'/v\d+$', '', url)

    def _secrets(self) -> list:
        """收集所有 API key 用于日志打码"""
        return [k for k in (
            self.gemini_key,
            self.openai_key,
            config.openai_backup_api_key,
        ) if k]

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

        # 按 image.providers 优先级依次尝试，任一成功即返回
        for provider in self.providers:
            image_path = await self._try_provider(provider, prompt)
            if image_path:
                return image_path

        logger.warning("⚠️ 图片生成失败，将以纯文本方式发布推文（不影响推文发送）")
        return None

    # ═══════════════════════════════════════════════════════════════
    # 提供商分发生图
    # ═══════════════════════════════════════════════════════════════

    async def _try_provider(self, provider: dict, prompt: str) -> Optional[str]:
        """按 provider.type 分发生图，成功返回路径，失败返回 None"""
        ptype = (provider.get('type') or 'gemini').lower()
        model = provider.get('model') or ''
        base_urls = provider.get('base_urls') or []
        if ptype == 'openai':
            return await self._try_openai(model, base_urls, prompt)
        return await self._try_gemini(model, base_urls, prompt)

    # ═══════════════════════════════════════════════════════════════
    # Gemini 生图 (generateContent 协议)
    # ═══════════════════════════════════════════════════════════════

    async def _try_gemini(self, model: str, base_urls: list, prompt: str) -> Optional[str]:
        """Gemini 协议生图，按 base_urls 优先级依次尝试，全部失败返回 None"""
        if not self.gemini_key:
            return None
        for base in base_urls:
            base = self._strip_api_version(base)
            url = (
                f"{base}/v1beta/models/{model}:generateContent"
                f"?key={self.gemini_key}"
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
                    logger.warning(f"Gemini 响应中未找到图片数据 [{model}@{base}]")
                    continue

                image_path = self._save_base64_image(
                    image_data.get('data', ''),
                    image_data.get('mime', 'image/png'),
                )
                if image_path:
                    logger.info(f"Gemini 图片生成成功 ({model}@{base}) → {image_path}")
                    return image_path

            except Exception as e:
                logger.warning(
                    f"Gemini 调用失败 [{model}@{base}]: {_redact(str(e), self._secrets())}"
                )

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
    # OpenAI 生图 (Chat Completions 协议)
    # ═══════════════════════════════════════════════════════════════

    async def _try_openai(self, model: str, base_urls: list, prompt: str) -> Optional[str]:
        """OpenAI (Images 生成) 协议生图，按 base_urls 优先级依次尝试。

        走 /images/generations 接口 (DALL-E 风格)，返回 b64_json 或 url。
        """
        if not self.openai_key:
            return None
        for base in base_urls:
            client = self._make_openai_client(
                self.openai_key,
                self._ensure_openai_base(base),
            )
            try:
                resp = client.images.generate(
                    model=model,
                    prompt=prompt,
                    n=1,
                    size="1024x1024",
                )
                img = resp.data[0] if resp.data else None
                if img is None:
                    logger.warning(f"OpenAI 返回空结果 [{model}@{base}]")
                    continue

                b64 = getattr(img, 'b64_json', None)
                if b64:
                    image_path = self._save_base64_image(b64, 'image/png')
                    if image_path:
                        logger.info(f"OpenAI 图片生成成功 ({model}@{base}) → {image_path}")
                        return image_path

                url = getattr(img, 'url', None)
                if url:
                    image_path = await self._download_image(url)
                    if image_path:
                        logger.info(f"OpenAI 图片生成成功 ({model}@{base}) → {image_path}")
                        return image_path

                logger.warning(f"OpenAI 响应中未找到图片数据 [{model}@{base}]")

            except Exception as e:
                logger.warning(
                    f"OpenAI 调用失败 [{model}@{base}]: {_redact(str(e), self._secrets())}"
                )

        return None

    @staticmethod
    def _ensure_openai_base(url: str) -> str:
        """确保 OpenAI base_url 以 /v1 结尾 (SDK 会拼接 /chat/completions)"""
        url = url.rstrip('/')
        if not url.endswith('/v1'):
            url += '/v1'
        return url

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
