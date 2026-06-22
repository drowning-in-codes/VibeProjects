"""
配置管理模块
从 config.yaml 和 .env 文件加载配置
"""
import os
import yaml
from pathlib import Path
from typing import Any, Dict
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class Config:
    """应用配置类"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self):
        """加载配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self._config = yaml.safe_load(f)

    def get(self, key: str, default=None) -> Any:
        """获取配置值，支持点号分隔的嵌套键"""
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default

            if value is None:
                return default

        return value

    @property
    def xactions_cli_path(self) -> str:
        """XActions CLI 路径"""
        return self.get('xactions.cli_path', './XActions/cli.js')

    @property
    def x_auth_token(self) -> str:
        """X 认证 Token"""
        token = os.getenv('X_AUTH_TOKEN', '')
        if not token:
            raise ValueError("请在 .env 文件中设置 X_AUTH_TOKEN")
        return token

    @property
    def anthropic_api_key(self) -> str:
        """Anthropic API Key"""
        key = os.getenv('ANTHROPIC_API_KEY', '')
        if not key:
            raise ValueError("请在 .env 文件中设置 ANTHROPIC_API_KEY")
        return key

    @property
    def anthropic_base_url(self) -> Optional[str]:
        """Anthropic API Base URL (可选)"""
        return os.getenv('ANTHROPIC_BASE_URL', None)

    @property
    def anthropic_model(self) -> str:
        """Anthropic 模型名称"""
        return self.get('anthropic.model', 'claude-opus-4-6')

    @property
    def anthropic_max_tokens(self) -> int:
        """Anthropic 最大 tokens"""
        return self.get('anthropic.max_tokens', 2000)

    @property
    def openai_api_key(self) -> Optional[str]:
        """OpenAI API Key (可选)"""
        return os.getenv('OPENAI_API_KEY', None)

    @property
    def openai_base_url(self) -> Optional[str]:
        """OpenAI API Base URL (可选)"""
        return os.getenv('OPENAI_BASE_URL', None)

    @property
    def database_path(self) -> str:
        """数据库文件路径"""
        return self.get('database.path', './data/tweets.db')

    @property
    def target_users(self) -> list:
        """目标用户列表"""
        users = self.get('targets.users', [])
        return [u['username'] for u in users if u.get('enabled', False)]

    @property
    def crawl_cron(self) -> str:
        """爬取任务 cron 表达式"""
        return self.get('scheduler.crawl_cron', '0 2 * * *')

    @property
    def post_interval_hours(self) -> int:
        """发布任务间隔（小时）"""
        return self.get('scheduler.post_interval_hours', 4)

    @property
    def log_level(self) -> str:
        """日志级别"""
        return self.get('logging.level', 'INFO')

    @property
    def log_file(self) -> str:
        """日志文件路径"""
        return self.get('logging.file', './logs/autotwit.log')

    @property
    def log_rotation(self) -> str:
        """日志轮转大小"""
        return self.get('logging.rotation', '100 MB')

    @property
    def zhihu_access_secret(self) -> Optional[str]:
        """知乎开放平台 Access Secret (Bearer Token)"""
        return os.getenv('ZHIHU_ACCESS_SECRET', None)

    @property
    def zhihu_chat_model(self) -> str:
        """知乎直答模型: fast / thinking / agent"""
        return self.get('zhihu.chat_model', 'fast')

    @property
    def log_retention(self) -> str:
        """日志保留时间"""
        return self.get('logging.retention', '30 days')


# 全局配置实例
config = Config()
