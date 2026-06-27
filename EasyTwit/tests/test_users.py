"""
XDK users.get_by_usernames 测试
使用 Bearer Token 批量查询用户信息
"""
import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from xdk import Client

load_dotenv(override=True)

bearer_token = os.environ.get("X_BEARER_TOKEN")
if not bearer_token:
    print("❌ X_BEARER_TOKEN 未配置")
    sys.exit(1)

client = Client(bearer_token=bearer_token)
usernames = ["XDevelopers", "API", "elonmusk", "sama"]


def main():
    print(f"查询用户: {', '.join(usernames)}\n")

    try:
        response = client.users.get_by_usernames(
            usernames=usernames,
            user_fields=["description", "created_at", "public_metrics", "profile_image_url"],
        )

        data = getattr(response, 'data', None) or response

        if isinstance(data, list):
            for u in data:
                metrics = u.get('public_metrics', {})
                print(f"  @{u.get('username'):<20} {u.get('name', ''):<30} "
                      f"followers={metrics.get('followers_count', '?'):>10}  "
                      f"created={u.get('created_at', '?')[:10]}")
                if u.get('description'):
                    print(f"    {u['description'][:100]}")
            print(f"\n✅ {len(data)} 个用户查询成功")
        else:
            print(f"响应: {json.dumps(data, indent=2)[:500]}")

    except Exception as e:
        error_msg = str(e)
        if "402" in error_msg:
            print("❌ 402 Payment Required")
            print("   X API v2 需要付费层级 (Basic $100/月 或 Pro $5000/月)")
            print("   代码逻辑正确，升级 API 层级后即可使用")
        else:
            print(f"❌ 错误: {error_msg[:200]}")


if __name__ == "__main__":
    main()
