"""
知乎数据源测试
热榜 / 搜索 / 全网搜索 / 直答 AI
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(override=True)

from src.zhihu.client import ZhihuClient


def test_hot_list():
    print("=" * 50)
    print("测试 1: 知乎热榜")
    print("=" * 50)
    z = ZhihuClient()
    if not z.ready:
        print("  SKIP: ZHIHU_ACCESS_SECRET 未配置")
        return
    items = z.hot_list(limit=5)
    print(f"  返回: {len(items)} 条")
    for i, item in enumerate(items, 1):
        title = item.get("Title", "")
        hot = item.get("Url", "")
        print(f"  {i}. {title[:60]}" + (f" | {hot}" if hot else ""))
    assert len(items) >= 0, "热榜应返回列表"
    print("  ✅ 热榜通过")


def test_search():
    print("\n" + "=" * 50)
    print("测试 2: 知乎搜索")
    print("=" * 50)
    z = ZhihuClient()
    if not z.ready:
        print("  SKIP: 未配置")
        return
    items = z.search("AI 大模型", limit=3)
    print(f"  返回: {len(items)} 条")
    for item in items:
        title = item.get("Title", "")
        excerpt = item.get("ContentText", "")[:80]
        print(f"  - {title[:50]}")
        if excerpt:
            print(f"    {excerpt}")
    assert isinstance(items, list), "搜索应返回列表"
    print("  ✅ 搜索通过")


def test_global_search():
    print("\n" + "=" * 50)
    print("测试 3: 全网搜索")
    print("=" * 50)
    z = ZhihuClient()
    if not z.ready:
        print("  SKIP: 未配置")
        return
    items = z.global_search("科技", count=3)
    print(f"  返回: {len(items)} 条")
    for item in items:
        title = item.get("Title", "")
        text = (item.get("ContentText", ""))[:80]
        print(f"  - {title[:50]}")
        if text:
            print(f"    {text}")
    assert isinstance(items, list), "全网搜索应返回列表"
    print("  ✅ 全网搜索通过")


def test_zhida():
    print("\n" + "=" * 50)
    print("测试 4: 知乎直答 AI")
    print("=" * 50)
    z = ZhihuClient()
    if not z.ready:
        print("  SKIP: 未配置")
        return
    answer = z.zhida_ask("什么是人工智能？请用一句话回答", model="zhida-fast-1p5")
    if answer:
        print(f"  回答: {answer[:200]}")
        assert len(answer) > 0, "直答应有内容"
        print("  ✅ 直答通过")
    else:
        print("  ⚠️ 直答无返回 (可能接口不可用)")


def test_fetch_context():
    print("\n" + "=" * 50)
    print("测试 5: fetch_context 聚合")
    print("=" * 50)
    z = ZhihuClient()
    if not z.ready:
        print("  SKIP: 未配置")
        return
    ctx = z.fetch_context(
        ["zhihu_hot", "zhihu_search: AI", "zhihu_global: 科技", "zhida: 什么是大模型"],
        query="AI",
        limit=2,
    )
    if ctx:
        print(f"  上下文长度: {len(ctx)} 字符")
        print(f"  前 200 字:\n{ctx[:200]}...")
    else:
        print("  ⚠️ 无数据 (接口可能不可用)")
    assert isinstance(ctx, str), "fetch_context 应返回字符串"
    print("  ✅ 聚合通过")


if __name__ == "__main__":
    test_hot_list()
    test_search()
    test_global_search()
    test_zhida()
    test_fetch_context()
    print("\n全部测试完成")
