基于 XDK Python SDK (OAuth 1.0a) 开发推特自动发帖功能。爬取帖子并利用AI分析生成人格，并利用人格发送帖子。

XDK文档: https://docs.x.com/xdks/python/authentication
PyPI: https://pypi.org/project/xdk/

## 项目结构

```
EasyTwit/
├── src/
│   ├── main.py            CLI入口 + 所有命令路由
│   ├── config.py          YAML+.env配置管理
│   ├── poster.py          推文发布整合（生成+发布+图片上传）
│   ├── scheduler.py       Cron定时调度器
│   ├── x/
│   │   ├── client.py      XDK OAuth 1.0a 客户端封装
│   │   ├── scraper.py     推文爬取器
│   │   └── auth.py        OAuth 1.0a 三步认证流程
│   ├── ai/
│   │   ├── persona.py     人格蒸馏+自定义生成 (OpenAI-compatible Chat API)
│   │   ├── generator.py   推文内容生成 (OpenAI-compatible Chat API)
│   │   ├── image.py       多提供商生图(Gemini/OpenAI协议)
│   │   └── fallback.py    API主备切换工具
│   └── storage/
│       ├── models.py      Tweet/Persona/PostHistory dataclass
│       └── database.py    SQLite异步持久化 (aiosqlite)
├── tests/
│   └── test_image_api.py  图片API测试
├── config.yaml / .env.example / requirements.txt
└── README.md
```

## 核心流程

1. `scrape` — XDK search/user_posts 爬取目标用户推文 → SQLite
2. `distill` — 模型 API 分析推文 → 提取人格(tone/vocabulary/topics/style_metrics)
3. `generate` — 模型 API 基于人格生成推文内容 + 智能配图判断
4. `post` — XDK posts.create 发布推文（+ 配图上传）
5. `run` — Cron定时调度上述流程

## CLI 命令

| 命令 | 说明 |
|------|------|
| `python -m src setup` | 初始化数据库和目录 + X client 验证 |
| `python -m src scrape` | 爬取目标用户推文 |
| `python -m src distill` | 蒸馏人格 |
| `python -m src persona-custom` | 创建自定义人格 |
| `python -m src generate [-t topic]` | 生成预览 |
| `python -m src post [-t topic]` | 生成并发布 |
| `python -m src run` | 启动定时调度 |
| `python -m src status` | 查看状态 |

## XDK API 接口使用

### 认证 (OAuth 1.0a)

```python
from xdk import Client
from xdk.oauth1_auth import OAuth1

auth = OAuth1(
    api_key=config.x_api_key,           # Consumer Key
    api_secret=config.x_api_secret,     # Consumer Secret
    callback="http://localhost:3000/callback",
    access_token=config.x_access_token,
    access_token_secret=config.x_access_token_secret,
)
client = Client(auth=auth)
```

环境变量 (.env):
```bash
X_API_KEY=               # Consumer Key (API Key)
X_API_SECRET=            # Consumer Secret (API Key Secret)
X_ACCESS_TOKEN=          # OAuth 1.0a Access Token
X_ACCESS_TOKEN_SECRET=   # OAuth 1.0a Access Token Secret
```

### 推文操作 (posts)

| 方法 | XDK 调用 | 说明 |
|------|----------|------|
| `post(text, media_ids)` | `client.posts.create(post_data={"text": ..., "media": {"media_ids": [...]}})` | 发布推文，支持媒体附件 |
| `reply(tweet_id, text)` | `client.posts.create(post_data={"text": ..., "reply": {"in_reply_to_tweet_id": id}})` | 回复推文 |
| `quote(tweet_id, text)` | `client.posts.create(post_data={"text": ..., "quote_tweet_id": id})` | 引用推文 |
| `delete(tweet_id)` | `client.posts.delete(id)` | 删除推文 |
| `like(tweet_id)` | `client.users.like_post(id)` | 点赞 |
| `repost(tweet_id)` | `client.users.repost_post(id)` | 转推 |

### 媒体上传 (media) — 三步流程

| 步骤 | XDK 调用 | 说明 |
|------|----------|------|
| INIT | `client.media.initialize_upload(file_name, file_size, media_type)` | 初始化上传，获取 media_id |
| APPEND | `client.media.append_upload(media_id, file_data, segment_index)` | 上传文件数据 |
| FINALIZE | `client.media.finalize_upload(media_id)` | 完成上传 |

### 搜索 (posts.search)

| 方法 | XDK 调用 | 说明 |
|------|----------|------|
| `search(query, count)` | `client.posts.search_recent(query, max_results)` | 搜索最近推文 |
| `search(query, count, recent=False)` | `client.posts.search_all(query, max_results)` | 全量搜索 |
| `search_user(username, count)` | `search("from:{username}")` | 搜索指定用户推文 |

### 用户 (users)

| 方法 | XDK 调用 | 说明 |
|------|----------|------|
| `whoami()` | `client.users.get_me()` | 当前认证用户信息 |
| `user_info(username)` | `client.users.get_by_username(username)` | 获取用户信息 |
| `user_posts(user_id, count)` | `client.users.get_posts(user_id, max_results)` | 获取用户推文列表 |
| `timeline(count)` | `client.users.get_timeline(max_results)` | 首页时间线 |

### XDK 响应格式

XDK 返回 Pydantic 模型，通过 `.data` (dict) 提取：
```python
def _unwrap(response) -> Optional[Dict]:
    if response is None: return None
    if hasattr(response, 'data'): return response.data
    if isinstance(response, dict): return response
    return None
```

## 图片生成链

按 `image.providers` 优先级依次尝试 (任一失败自动切换下一个):

```
1. nano-banana-2                   (Gemini 协议) → autorouter.net → autorouter.io
2. gemini-3.1-flash-image-preview  (Gemini 协议) → autorouter.net → autorouter.io
3. gpt-image-2                     (Chat Completions) → autorouter.net → autorouter.io
    ↓ 全部失败
纯文本发布 (不阻断)
```

Gemini 生图接口 (`type: gemini`):
```
POST {base}/v1beta/models/{model}:generateContent?key={api_key}
Body: {"contents": [{"parts": [{"text": "prompt"}]}]}
Response: candidates[0].content.parts[].inlineData.data (base64)
```

配置项 (`config.yaml`):
```yaml
image:
  providers:                  # 生图提供商 (按优先级从高到低)
    - type: gemini            # generateContent 协议, key: GEMINI_API_KEY
      model: nano-banana-2
      base_urls:
        - https://autorouter.net
        - https://autorouter.io
    - type: openai            # Chat Completions 协议, key: OPENAI_API_KEY
      model: gpt-image-2
      base_urls:
        - https://autorouter.net
        - https://autorouter.io
```
环境变量: `GEMINI_API_KEY` (兼容旧 `NANOBANANA_API_KEY`) / `OPENAI_API_KEY`

## API 主备切换

所有 AI/图片 API 支持主备:
- 模型 API: `AI_BASE_URL` → `AI_BACKUP_BASE_URL`
  （旧的 `ANTHROPIC_*` / `MODEL_*` 变量仍兼容）
- 图片: Gemini → GPT-Image-2 → OpenAI Backup
- 切换逻辑: `ai/fallback.py` — `try_with_fallback()`

## 开发注意事项

- XDK 需 OAuth 1.0a 四件套，在 X Developer Portal → Keys and Tokens 获取
- config.py 支持代理 (HTTPS_PROXY环境变量)
- 数据库: SQLite, 异步访问 (aiosqlite)
- 图片: 多提供商按优先级生图 (image.providers: gemini/openai 协议)，下载到 data/images/
- 日志: loguru, 输出到控制台 + logs/easytwit.log
- XDK 版本: 0.1.0, 返回 Pydantic 模型 (.data 获取 dict)
