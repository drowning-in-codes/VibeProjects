"""
生图测试 — 使用当前 config.yaml + .env 配置
直接走 ImageManager 生产链路: Gemini(主) → GPT-Image-2(备) → 纯文本降级

用法:
    python tests/test_image_generate.py
    python tests/test_image_generate.py "一只戴墨镜的柴犬"   # 自定义 prompt
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(override=True)

from src.config import config
from src.ai.image import ImageManager


def _mask(key: str) -> str:
    """只显示 key 前后几字符，避免泄露完整密钥"""
    if not key:
        return "(未配置)"
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


async def main():
    print("=" * 60)
    print("当前生图配置")
    print("=" * 60)
    print(f"image.enabled      : {config.image_enabled}")
    print(f"gemini.model       : {config.gemini_model}")
    print(f"gemini.base_urls   : {config.gemini_base_urls}")
    print(f"gemini.api_key     : {_mask(config.gemini_api_key)}")
    print(f"openai.base_url    : {config.openai_base_url or '(官方)'}")
    print(f"openai.model       : {config.get('openai.model', 'gpt-image-2')}")
    print(f"openai.api_key     : {_mask(config.openai_api_key)}")
    print()

    # 实际拼出来的 Gemini URL (key 打码)
    if config.gemini_api_key:
        from src.ai.image import ImageManager as IM
        base = IM._strip_api_version(config.gemini_base_urls[0])
        url = (f"{base}/v1beta/models/{config.gemini_model}:generateContent"
               f"?key=***")
        print(f"Gemini 实际 URL (最高优先级) : {url}")
        print()

    prompt = sys.argv[1] if len(sys.argv) > 1 else "AI会改变未来"

    print("=" * 60)
    print(f"测试生成: {prompt}")
    print("=" * 60)

    mgr = ImageManager()
    result = await mgr.get_image_for_tweet(prompt, topic="科技")

    print()
    if result:
        print(f"✅ 生图成功: {result}")
    else:
        print("⚠️  生图失败 (会以纯文本降级，不影响发帖)")


if __name__ == "__main__":
    asyncio.run(main())
