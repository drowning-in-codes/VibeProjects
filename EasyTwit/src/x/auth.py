"""
X/Twitter OAuth 1.0a 认证流程
三步认证: request_token → 浏览器授权 → access_token
"""
import json
import asyncio
import webbrowser
from pathlib import Path
from typing import Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread
from urllib.parse import urlparse, parse_qs
from loguru import logger
from xdk.oauth1_auth import OAuth1, OAuth1RequestToken

from ..config import config


# 状态缓存文件（跨进程保存 request_token）
STATE_FILE = Path("./data/oauth_state.json")


def _save_state(oauth_token: str, oauth_token_secret: str):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({
        "oauth_token": oauth_token,
        "oauth_token_secret": oauth_token_secret,
    }))


def _load_state() -> Optional[dict]:
    if not STATE_FILE.exists():
        return None
    return json.loads(STATE_FILE.read_text())


def _clear_state():
    if STATE_FILE.exists():
        STATE_FILE.unlink()


def _update_env(access_token: str, access_token_secret: str):
    """将 access_token 写入 .env 文件"""
    env_path = Path(".env")
    if not env_path.exists():
        logger.error(".env 文件不存在")
        return

    lines = env_path.read_text().splitlines()
    updated = []
    keys_updated = {"X_ACCESS_TOKEN": False, "X_ACCESS_TOKEN_SECRET": False}

    for line in lines:
        for key, val in [
            ("X_ACCESS_TOKEN", access_token),
            ("X_ACCESS_TOKEN_SECRET", access_token_secret),
        ]:
            if line.startswith(f"{key}="):
                updated.append(f"{key}={val}")
                keys_updated[key] = True
                break
        else:
            updated.append(line)

    # 追加不存在的 key
    for key, written in keys_updated.items():
        if not written:
            val = access_token if key == "X_ACCESS_TOKEN" else access_token_secret
            updated.append(f"{key}={val}")

    env_path.write_text("\n".join(updated) + "\n")
    logger.success(f"Token 已写入 .env: X_ACCESS_TOKEN 和 X_ACCESS_TOKEN_SECRET")


async def oauth_flow(port: int = 8000):
    """OAuth 1.0a 三步认证流程"""
    if not config.x_api_key or not config.x_api_secret:
        logger.error("请先在 .env 中配置 X_API_KEY 和 X_API_SECRET")
        return

    callback_url = f"http://localhost:{port}/callback"
    auth = OAuth1(
        api_key=config.x_api_key,
        api_secret=config.x_api_secret,
        callback=callback_url,
    )

    # ── Step 1: 获取 request_token ────────────────────────
    logger.info("Step 1: 获取 request_token...")
    try:
        request_token = auth.get_request_token()
    except Exception as e:
        logger.error(f"获取 request_token 失败: {e}")
        return

    # 缓存到文件（跨进程持久化）
    _save_state(request_token.oauth_token, request_token.oauth_token_secret)
    logger.info(f"  request_token 已缓存: {request_token.oauth_token[:20]}...")

    # ── Step 2: 浏览器授权 ────────────────────────────────
    auth_url = auth.get_authorization_url(request_token)
    logger.info(f"Step 2: 打开浏览器授权...")
    logger.info(f"  URL: {auth_url}")

    # 启动本地 web 服务器接收回调
    verifier: Optional[str] = None

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal verifier
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            if parsed.path == "/callback":
                verifier = params.get("oauth_verifier", [None])[0]
                if verifier:
                    self.send_response(200)
                    self.send_header("Content-type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(b"<h1>EasyTwit</h1><p>OAuth success! You can close this page.</p>")
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Missing oauth_verifier")
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, format, *args):
            pass  # suppress HTTP server logs

    server = HTTPServer(("127.0.0.1", port), CallbackHandler)
    server.timeout = 1

    def serve():
        while verifier is None:
            server.handle_request()

    thread = Thread(target=serve, daemon=True)
    thread.start()

    # 打开浏览器
    webbrowser.open(auth_url) if config.x_api_key else logger.info(f"请手动打开: {auth_url}")

    # 等待回调（最多 5 分钟）
    logger.info("  等待浏览器授权完成...")
    for i in range(300):
        if verifier:
            break
        await asyncio.sleep(1)
    server.shutdown()

    if not verifier:
        logger.error("授权超时（5分钟）")
        return

    logger.info(f"  收到 oauth_verifier: {verifier[:10]}...")

    # ── Step 3: 获取 access_token ─────────────────────────
    logger.info("Step 3: 交换 access_token...")
    try:
        access_token_obj = auth.get_access_token(request_token, verifier)
    except Exception as e:
        logger.error(f"获取 access_token 失败: {e}")
        _clear_state()
        return

    access_token = access_token_obj.access_token
    access_token_secret = access_token_obj.access_token_secret

    logger.success("OAuth 认证完成!")
    logger.info(f"  Access Token:       {access_token[:25]}...")
    logger.info(f"  Access Token Secret: {access_token_secret[:15]}...")

    # ── 写入 .env ─────────────────────────────────────────
    _update_env(access_token, access_token_secret)
    _clear_state()
    logger.success("已写入 .env 文件")
