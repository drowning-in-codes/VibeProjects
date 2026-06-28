"""
配置管理模块
从 config.yaml 和 .env 加载配置，支持点号分隔的嵌套键访问。
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

load_dotenv(override=True)


class Config:
    """应用配置类，聚合 YAML 文件与环境变量。"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self):
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}

    def get(self, key: str, default=None) -> Any:
        """获取配置值，key 支持点号分隔的嵌套路径（如 'ai.model'）。"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            if value is None:
                return default
        return value

    # ── PushPlus ────────────────────────────────────────

    @property
    def pushplus_token(self) -> str:
        token = os.getenv("PUSHPLUS_TOKEN", "")
        if not token:
            raise ValueError("请在 .env 文件中设置 PUSHPLUS_TOKEN")
        return token

    @property
    def pushplus_channel(self) -> str:
        return self.get("pushplus.channel", "wechat")

    # ── AI / LLM ────────────────────────────────────────

    @property
    def ai_api_key(self) -> Optional[str]:
        return os.getenv("AI_API_KEY", None)

    @property
    def ai_base_url(self) -> str:
        return os.getenv("AI_BASE_URL", "https://api.deepseek.com/v1")

    @property
    def ai_model(self) -> str:
        return self.get("ai.model", "deepseek-chat")

    @property
    def ai_max_tokens(self) -> int:
        return self.get("ai.max_tokens", 400)

    @property
    def ai_temperature(self) -> float:
        return self.get("ai.temperature", 0.7)

    @property
    def ai_system_prompt(self) -> str:
        return self.get(
            "ai.system_prompt",
            "你是B站直播内容分析师，擅长从弹幕中提取关键信息。",
        )

    @property
    def ai_enabled(self) -> bool:
        return self.ai_api_key is not None and self.ai_api_key.strip() != ""

    # ── Bilibili ────────────────────────────────────────

    @property
    def blive_session_file(self) -> str:
        return self.get("bilibili.session_file", "./data/session.json")

    @property
    def blive_following_file(self) -> str:
        return self.get("bilibili.following_file", "./data/following.yaml")

    @property
    def blive_history_file(self) -> str:
        return self.get("bilibili.history_file", "./data/history.json")

    @property
    def bili_sessdata(self) -> Optional[str]:
        return os.getenv("BILI_SESSDATA", None)

    @property
    def bili_jct(self) -> Optional[str]:
        return os.getenv("BILI_BILI_JCT", None)

    @property
    def bili_dedeuserid(self) -> Optional[str]:
        return os.getenv("BILI_DEDEUSERID", None)

    @property
    def has_cookie_env(self) -> bool:
        return bool(self.bili_sessdata)

    # ── Monitor ─────────────────────────────────────────

    @property
    def monitor_whitelist(self) -> list:
        return self.get("monitor.whitelist", [])

    @property
    def monitor_danmaku_sample_count(self) -> int:
        return self.get("monitor.danmaku_sample_count", 500)

    @property
    def monitor_api_delay(self) -> float:
        return self.get("monitor.api_delay", 1.5)

    # ── Scheduler ───────────────────────────────────────

    @property
    def schedule_cron(self) -> str:
        return self.get("scheduler.report_cron", "0 22 * * *")

    # ── Logging ─────────────────────────────────────────

    @property
    def log_level(self) -> str:
        return self.get("logging.level", "INFO")

    @property
    def log_file(self) -> str:
        return self.get("logging.file", "./logs/blive.log")

    @property
    def log_rotation(self) -> str:
        return self.get("logging.rotation", "10 MB")

    @property
    def log_retention(self) -> str:
        return self.get("logging.retention", "30 days")

    # ── Word Cloud ──────────────────────────────────────

    @property
    def wordcloud_output_dir(self) -> str:
        return self.get("wordcloud.output_dir", "./output/wordcloud")

    @property
    def wordcloud_width(self) -> int:
        return self.get("wordcloud.width", 800)

    @property
    def wordcloud_height(self) -> int:
        return self.get("wordcloud.height", 600)

    @property
    def wordcloud_font_path(self) -> str:
        return self.get("wordcloud.font_path", "")

    @property
    def wordcloud_bg_color(self) -> str:
        return self.get("wordcloud.background_color", "white")

    @property
    def wordcloud_max_words(self) -> int:
        return self.get("wordcloud.max_words", 200)


# 全局单例
config = Config()
