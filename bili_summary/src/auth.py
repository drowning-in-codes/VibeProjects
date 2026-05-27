"""B站登录认证模块"""

import json
import os
import sys
from bilibili_api import Credential, sync
from bilibili_api.login import login_with_qrcode

from src.config import CREDENTIAL_PATH


class BiliAuth:
    def __init__(self, config: dict):
        self.config = config
        self.credential: Credential | None = None
        self._load_credential()

    def _load_credential(self):
        """从缓存文件加载登录态"""
        if os.path.exists(CREDENTIAL_PATH):
            with open(CREDENTIAL_PATH, "r") as f:
                data = json.load(f)
            self.credential = Credential(
                sessdata=data.get("sessdata", ""),
                bili_jct=data.get("bili_jct", ""),
                dedeuserid=data.get("dedeuserid", ""),
            )

    def _save_credential(self):
        """持久化登录态"""
        if self.credential:
            os.makedirs(os.path.dirname(CREDENTIAL_PATH), exist_ok=True)
            with open(CREDENTIAL_PATH, "w") as f:
                json.dump({
                    "sessdata": self.credential.sessdata,
                    "bili_jct": self.credential.bili_jct,
                    "dedeuserid": self.credential.dedeuserid,
                }, f, indent=2)
            print(f"登录态已保存到 {CREDENTIAL_PATH}")

    def login_by_qrcode(self):
        """扫码登录"""
        try:
            credential = sync(login_with_qrcode())
            if isinstance(credential, Credential):
                self.credential = credential
            self._save_credential()
        except Exception as e:
            print(f"扫码登录失败: {e}")
            sys.exit(1)

    def login_by_cookie(self):
        """通过配置文件中的cookie登录"""
        bili = self.config.get("bilibili", {})
        sessdata = bili.get("sessdata", "")
        if not sessdata:
            print("请在 config.yaml 的 bilibili.sessdata 中填入cookie")
            sys.exit(1)
        self.credential = Credential(
            sessdata=sessdata,
            bili_jct=bili.get("bili_jct", ""),
            dedeuserid=bili.get("dedeuserid", ""),
        )
        self._save_credential()

    def is_logged_in(self) -> bool:
        """检查是否已登录"""
        if not self.credential:
            return False
        return bool(self.credential.sessdata)

    def get_credential(self) -> Credential | None:
        return self.credential if self.is_logged_in() else None
