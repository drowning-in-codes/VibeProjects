"""
配置管理模块
从 config.yaml 和 .env 文件加载配置
"""
import os
import httpx
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv

# 加载环境变量（override=True 确保 .env 覆盖系统变量）
load_dotenv(override=True)


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

    # ── X/Twitter (XDK OAuth 1.0a) ────────────────────────

    @property
    def x_api_key(self) -> Optional[str]:
        """X API Key (Consumer Key)"""
        return os.getenv('X_API_KEY', None)

    @property
    def x_api_secret(self) -> Optional[str]:
        """X API Secret (Consumer Secret)"""
        return os.getenv('X_API_SECRET', None)

    @property
    def x_access_token(self) -> Optional[str]:
        """X Access Token"""
        return os.getenv('X_ACCESS_TOKEN', None)

    @property
    def x_access_token_secret(self) -> Optional[str]:
        """X Access Token Secret"""
        return os.getenv('X_ACCESS_TOKEN_SECRET', None)

    @property
    def x_bearer_token(self) -> Optional[str]:
        """X Bearer Token (App-only, 用于趋势等公开接口)"""
        return os.getenv('X_BEARER_TOKEN', None)

    @property
    def x_client_id(self) -> Optional[str]:
        """X OAuth 2.0 Client ID"""
        return os.getenv('X_CLIENT_ID', None)

    @property
    def x_client_secret(self) -> Optional[str]:
        """X OAuth 2.0 Client Secret"""
        return os.getenv('X_CLIENT_SECRET', None)

    @property
    def x_redirect_uri(self) -> Optional[str]:
        """X OAuth 2.0 Redirect URI"""
        return os.getenv('X_REDIRECT_URI', 'http://localhost:8080/callback')

    @property
    def zhihu_access_secret(self) -> Optional[str]:
        """知乎开放平台 Access Secret (Bearer Token)"""
        return os.getenv('ZHIHU_ACCESS_SECRET', None)

    @property
    def x_timeout(self) -> int:
        """X API 请求超时（秒）"""
        return self.get('x.timeout', 30)

    # ── Anthropic (Claude) ────────────────────────────────

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
    def anthropic_backup_api_key(self) -> Optional[str]:
        """Anthropic 备用 API Key"""
        return os.getenv('ANTHROPIC_BACKUP_API_KEY', None)

    @property
    def anthropic_backup_base_url(self) -> Optional[str]:
        """Anthropic 备用 API Base URL"""
        return os.getenv('ANTHROPIC_BACKUP_BASE_URL', None)

    @property
    def anthropic_model(self) -> str:
        """Anthropic 模型名称"""
        return self.get('anthropic.model', 'claude-sonnet-4-6')

    @property
    def anthropic_max_tokens(self) -> int:
        """Anthropic 最大 tokens"""
        return self.get('anthropic.max_tokens', 2000)

    @property
    def prompt_template(self) -> str:
        """预备 prompt 模板路径 (prompts/*.md 或空)"""
        return self.get('anthropic.prompt_template', '')

    # ── nanobanana (Gemini 2.5 Flash Image) ───────────────

    @property
    def nanobanana_api_key(self) -> Optional[str]:
        """nanobanana API Key"""
        return os.getenv('NANOBANANA_API_KEY', None)

    @property
    def nanobanana_base_url(self) -> str:
        """nanobanana API Base URL"""
        return os.getenv('NANOBANANA_BASE_URL', 'https://autorouter.io')

    @property
    def nanobanana_model(self) -> str:
        """nanobanana 模型名称"""
        return self.get('nanobanana.model', 'nano-banana')

    # ── OpenAI (DALL-E) ───────────────────────────────────

    @property
    def openai_api_key(self) -> Optional[str]:
        """OpenAI API Key"""
        return os.getenv('OPENAI_API_KEY', None)

    @property
    def openai_base_url(self) -> Optional[str]:
        """OpenAI API Base URL (可选)"""
        return os.getenv('OPENAI_BASE_URL', None)

    @property
    def openai_backup_api_key(self) -> Optional[str]:
        """OpenAI 备用 API Key"""
        return os.getenv('OPENAI_BACKUP_API_KEY', None)

    @property
    def openai_backup_base_url(self) -> Optional[str]:
        """OpenAI 备用 API Base URL"""
        return os.getenv('OPENAI_BACKUP_BASE_URL', None)

    # ── Targets ───────────────────────────────────────────

    @property
    def target_users(self) -> list:
        """目标用户列表（启用的）"""
        users = self.get('targets.users', [])
        return [u['username'] for u in users if u.get('enabled', False)]

    @property
    def scrape_source(self) -> str:
        """爬取来源: users | following | timeline"""
        return self.get('targets.scrape_source', 'users')

    @property
    def persona_template(self) -> str:
        """兼容旧接口"""
        return self.get('targets.persona_template', '')

    @property
    def persona_group(self) -> str:
        """人格组 (random | tech | social | career | finance)"""
        return self.get('targets.persona_group', 'random')

    @property
    def group_weights(self) -> dict:
        """随机选组权重配置"""
        return self.get('targets.group_weights', {
            'tech': 40, 'career': 25, 'social': 20, 'finance': 15
        })

    @property
    def reference_tweet_count(self) -> int:
        """生成时带入的参考推文数"""
        return self.get('targets.reference_tweet_count', 2)

    # ── Scheduler ─────────────────────────────────────────

    @property
    def post_cron(self) -> str:
        """发帖 cron"""
        return self.get('scheduler.post_cron', '0 */4 * * *')

    @property
    def distill_cron(self) -> str:
        """爬取蒸馏 cron (如 "0 0 */14 * *" 每两周)"""
        return self.get('scheduler.distill_cron', '0 0 */14 * *')

    @property
    def max_posts_per_day(self) -> int:
        """每日最大发帖数 (支持范围 [min, max] 或固定值)"""
        import random
        from datetime import date
        val = self.get('scheduler.max_posts_per_day', 6)
        if isinstance(val, list) and len(val) == 2:
            # 按天缓存, 同一天返回同一个随机值
            today = date.today().isoformat()
            if not hasattr(self, '_daily_limit_cache'):
                self._daily_limit_cache = {}
            if today not in self._daily_limit_cache:
                self._daily_limit_cache = {today: random.randint(val[0], val[1])}
            return self._daily_limit_cache[today]
        return int(val) if val else 6

    @property
    def run_immediately(self) -> bool:
        """启动后立即执行一次"""
        return self.get('scheduler.run_immediately', True)

    @property
    def jitter_minutes(self) -> int:
        """定时任务时间扰动 (分钟)"""
        return self.get('scheduler.jitter_minutes', 30)

    # ── Database ──────────────────────────────────────────

    @property
    def database_path(self) -> str:
        """数据库文件路径"""
        return self.get('database.path', './data/easytwit.db')

    # ── Image ─────────────────────────────────────────────

    @property
    def image_enabled(self) -> bool:
        """是否启用图片生成"""
        return self.get('image.enabled', True)

    @property
    def image_output_dir(self) -> str:
        """图片输出目录"""
        return self.get('image.output_dir', './data/images')

    # ── Logging ───────────────────────────────────────────

    @property
    def log_level(self) -> str:
        """日志级别"""
        return self.get('logging.level', 'INFO')

    @property
    def log_file(self) -> str:
        """日志文件路径"""
        return self.get('logging.file', './logs/easytwit.log')

    @property
    def log_rotation(self) -> str:
        """日志轮转大小"""
        return self.get('logging.rotation', '100 MB')

    @property
    def log_retention(self) -> str:
        """日志保留时间"""
        return self.get('logging.retention', '30 days')

    # ── Proxy ─────────────────────────────────────────────

    @property
    def http_proxy(self) -> Optional[str]:
        """HTTP/HTTPS 代理地址"""
        return (
            os.getenv('HTTPS_PROXY', None)
            or os.getenv('HTTP_PROXY', None)
            or self.get('proxy.url', None)
        )

    def get_proxies_dict(self) -> Optional[Dict[str, str]]:
        """返回 requests 库兼容的代理字典"""
        url = self.http_proxy
        if url:
            return {"http": url, "https": url}
        return None

    def get_httpx_client(self) -> Optional[httpx.Client]:
        """返回配置了代理的 httpx 同步客户端"""
        url = self.http_proxy
        if url:
            return httpx.Client(proxy=url, trust_env=False)
        return None


# 全局配置实例
config = Config()
