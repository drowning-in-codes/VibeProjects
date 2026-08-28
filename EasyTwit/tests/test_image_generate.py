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
    print("当前生图配置 (按优先级)")
    print("=" * 60)
    print(f"image.enabled      : {config.image_enabled}")
    print(f"gemini.api_key     : {_mask(config.gemini_api_key)}")
    print(f"openai.api_key     : {_mask(config.openai_api_key)}")
    print()
    for i, p in enumerate(config.image_providers, 1):
        ptype = p.get('type', 'gemini')
        model = p.get('model', '?')
        base_urls = p.get('base_urls', [])
        key = config.gemini_api_key if ptype == 'gemini' else config.openai_api_key
        print(f"[{i}] {ptype:6s} {model}  (key: {_mask(key)})")
        for u in base_urls:
            print(f"      └─ {u}")
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
