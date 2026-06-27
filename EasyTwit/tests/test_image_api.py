"""
EasyTwit 图片生成 API 测试
nanobanana (Gemini API) + GPT-Image-2 (Chat Completions)
"""
import os
import sys
import json
import httpx
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(override=True)

API_KEY = os.getenv("NANOBANANA_API_KEY", "")
BASE_URL = os.getenv("NANOBANANA_BASE_URL", "https://autorouter.io")
GPT_KEY = os.getenv("OPENAI_API_KEY", "")
GPT_URL = os.getenv("OPENAI_BASE_URL", "https://autorouter.io/v1")

PROMPT = "A beautiful sunset over a calm ocean, minimalist pastel colors, peaceful atmosphere"

print(f"nanobanana:   {BASE_URL}")
print(f"GPT-Image-2:  {GPT_URL}")
print()

# ═══════════════════════════════════════════════════════════════
# 测试 1: nanobanana (Gemini API)
# ═══════════════════════════════════════════════════════════════

print("=" * 60)
print("测试 1: nanobanana (Gemini 2.5 Flash Image)")
print("=" * 60)

url = f"{BASE_URL}/v1beta/models/gemini-2.5-flash-image-preview:generateContent?key={API_KEY}"
body = {"contents": [{"parts": [{"text": PROMPT}]}]}

try:
    with httpx.Client(timeout=120) as c:
        resp = c.post(url, json=body)
        print(f"   HTTP {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for i, p in enumerate(parts):
                    if "inlineData" in p:
                        mime = p["inlineData"].get("mimeType", "?")
                        size = len(p["inlineData"].get("data", ""))
                        print(f"   ✅ part[{i}]: {mime}, {size} bytes (base64)")
                    elif "text" in p:
                        print(f"   ✅ part[{i}]: text ({len(p['text'])} chars)")
                        print(f"      {p['text'][:200]}...")
            else:
                print(f"   ⚠️  no candidates")
                print(f"   Response: {json.dumps(data, indent=2)[:300]}")
        else:
            print(f"   ❌ {resp.text[:200]}")
except Exception as e:
    print(f"   ❌ 请求失败: {e}")

print()

# ═══════════════════════════════════════════════════════════════
# 测试 2: GPT-Image-2 (Chat Completions)
# ═══════════════════════════════════════════════════════════════

print("=" * 60)
print("测试 2: GPT-Image-2 (Chat Completions)")
print("=" * 60)

try:
    client = OpenAI(base_url=GPT_URL, api_key=GPT_KEY)
    completion = client.chat.completions.create(
        model="gpt-image-2",
        messages=[{"role": "user", "content": PROMPT}],
    )
    content = completion.choices[0].message.content
    print(f"   ✅ 模型: {completion.model}")
    print(f"   响应 (前 200 字): {content[:200]}")
except Exception as e:
    print(f"   ❌ 失败: {e}")

print()

# ═══════════════════════════════════════════════════════════════
# 测试 3: EasyTwit ImageManager 集成
# ═══════════════════════════════════════════════════════════════

print("=" * 60)
print("测试 3: EasyTwit ImageManager 集成")
print("=" * 60)

from src.ai.image import ImageManager
import asyncio

async def test_integration():
    mgr = ImageManager()
    result = await mgr.get_image_for_tweet("AI会改变未来", "科技")
    if result:
        print(f"   ✅ 图片生成成功: {result}")
    else:
        print(f"   ⚠️  图片生成失败 (纯文本降级)")

asyncio.run(test_integration())

print()
print("测试完成")
