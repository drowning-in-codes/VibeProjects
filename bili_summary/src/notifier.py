"""推送模块"""

import requests


class PushNotifier:
    def __init__(self, config: dict):
        push = config.get("push", {})
        self.token = push.get("pushplus_token", "")

    def send(self, content: str, title: str = "B站直播日报") -> bool:
        """通过 PushPlus 推送日报"""
        if not self.token:
            print("未配置 pushplus_token，跳过推送")
            return False

        try:
            resp = requests.post(
                "https://www.pushplus.plus/send",
                json={
                    "token": self.token,
                    "title": title,
                    "content": content,
                    "template": "txt",
                },
                timeout=10,
            )
            data = resp.json()
            if data.get("code") == 200:
                print("推送成功")
                return True
            else:
                print(f"推送失败: {data.get('msg', resp.text)}")
                return False
        except Exception as e:
            print(f"推送请求异常: {e}")
            return False
