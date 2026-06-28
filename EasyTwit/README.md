# EasyTwit

基于 **XDK Python SDK** + **OAuth 1.0a** 的 X/Twitter 自动发帖应用。

> 爬取推文 → AI 蒸馏人格 → 用人格自动发推

XDK 文档: https://docs.x.com/xdks/python/reference/modules

## 架构

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ 爬取推文  │ →  │ 蒸馏人格  │ →  │ 生成推文  │ →  │ 定时发布  │
│ XDK       │    │ Claude   │    │ Claude   │    │ XDK       │
│ search    │    │ analyze  │    │ generate │    │ post      │
└──────────┘    └──────────┘    └──────────┘    └──────────┘
```

## 前置条件

### 1. X Developer Portal 配置

1. 在 [developer.x.com](https://developer.x.com/en/portal/dashboard) 创建 App
2. "Keys and Tokens" → 生成 **Consumer Keys** (API Key + Secret)
3. 生成 **Access Token & Secret** (OAuth 1.0a, Read & Write 权限)
4. 生成 **Bearer Token** (用于趋势等公开接口)

### 2. 配置 .env

```bash
cp .env.example .env
```

必填:
```bash
ANTHROPIC_API_KEY=sk-ant-...          # Claude API
X_API_KEY=...                          # Consumer Key
X_API_SECRET=...                       # Consumer Secret
X_ACCESS_TOKEN=...                     # OAuth 1.0a Access Token
X_ACCESS_TOKEN_SECRET=...              # OAuth 1.0a Access Token Secret
```

可选:
```bash
X_BEARER_TOKEN=...                     # Bearer Token (趋势接口)
NANOBANANA_API_KEY=sk-...              # 图片生成 (主)
OPENAI_API_KEY=sk-...                  # 图片生成 (备)
```

或使用 OAuth 自动认证 (仅需 API Key + Secret):
```bash
python -m src auth          # 浏览器授权 → 自动写入 .env
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. Docker 部署 (可选)

```bash
# 构建镜像
docker build -t easytwit .

# 初始化数据库
docker run --rm \
  -v ./data:/app/data \
  -v ./.env:/app/.env \
  easytwit python -m src setup

# 交互式创建人格
docker run -it --rm \
  -v ./.env:/app/.env \
  -v ./data:/app/data \
  easytwit python -m src persona-custom

# 手动发帖
docker run --rm \
  -v ./.env:/app/.env \
  -v ./data:/app/data \
  easytwit python -m src post -t "AI"

# 后台运行定时调度
docker compose up -d

# 查看状态
docker compose run --rm easytwit python -m src status

# 查看日志
docker compose logs -f

# 停止
docker compose down
```

## CLI 命令

| 命令 | 说明 |
|------|------|
| `python -m src auth` | OAuth 1.0a 浏览器认证 |
| `python -m src setup` | 初始化数据库和目录 |
| `python -m src scrape` | 爬取 config.yaml 中配置的目标用户 |
| `python -m src scrape -u username` | 按用户名爬取 |
| `python -m src scrape -i user_id` | 按 ID 爬取 |
| `python -m src scrape -u elonmusk -n 50` | 指定用户 + 数量 |
| `python -m src distill` | 从推文蒸馏人格 |
| `python -m src persona-custom` | 交互式创建自定义人格 |
| `python -m src persona-custom --config` | 从 config.yaml 读取人格配置 |
| `python -m src generate [-t topic]` | 生成推文预览 |
| `python -m src post [-t topic]` | 生成并发布推文 |
| `python -m src trends [-w worldwide]` | 查看趋势 |
| `python -m src trends -p` | 个性趋势 |
| `python -m src run` | 启动定时调度器 |
| `python -m src status` | 查看应用状态 |

## 项目结构

```
EasyTwit/
├── src/
│   ├── main.py               # CLI 入口 + 命令路由
│   ├── config.py             # YAML + .env 配置管理
│   ├── poster.py             # 推文发布整合 (生成+上传+发布)
│   ├── scheduler.py          # Cron 定时调度器
│   ├── x/
│   │   ├── client.py         # XDK 客户端 (posts/search/users/media/trends)
│   │   ├── scraper.py        # 推文爬取器
│   │   └── auth.py           # OAuth 1.0a 三步认证 (web服务器+浏览器)
│   ├── ai/
│   │   ├── persona.py        # 人格蒸馏 + 交互式自定义生成
│   │   ├── generator.py      # 推文内容生成 + 智能配图判断
│   │   ├── image.py          # nanobanana(主) + GPT-Image-2(备) 配图
│   │   └── fallback.py       # API 主备切换工具
│   └── storage/
│       ├── models.py         # Tweet / Persona / PostHistory
│       └── database.py       # SQLite 异步持久化
├── tests/
│   ├── test_image_api.py     # 图片 API 测试
│   └── test_users.py         # 用户查询 API 测试
├── Dockerfile / docker-compose.yml / .dockerignore
├── config.yaml / .env.example / requirements.txt
└── README.md
```

## 配置

### config.yaml

```yaml
# 目标用户 (爬取+蒸馏人格)
targets:
  users:
    - username: elonmusk
      enabled: true
  # 自定义人格 (--config 模式读取)
  custom_persona:
    enabled: true
    description: "一个关注AI和科技前沿的理性思考者"
    keywords: [AI, 科技, 编程, 创业]
    tone: "专业、理性、偶尔幽默"
    topics: [人工智能, 开源技术, 科技趋势]

# 定时调度
scheduler:
  post_cron: "0 */4 * * *"   # 每4小时
  max_posts_per_day: 6

# 图片生成模型
nanobanana:
  model: nano-banana
```

### .env 完整配置

```bash
# ── X/Twitter ──
X_API_KEY=...                          # Consumer Key (API Key)
X_API_SECRET=...                       # Consumer Secret
X_ACCESS_TOKEN=...                     # OAuth 1.0a Access Token
X_ACCESS_TOKEN_SECRET=...              # OAuth 1.0a Access Token Secret
X_BEARER_TOKEN=...                     # Bearer Token (趋势接口, 可选)

# ── Claude API ──
ANTHROPIC_API_KEY=sk-ant-...
# ANTHROPIC_BASE_URL=https://api.anthropic.com
# ANTHROPIC_BACKUP_API_KEY=...         # 备用, 主失败自动切换
# ANTHROPIC_BACKUP_BASE_URL=...

# ── 图片生成 ──
# Primary: nanobanana (Gemini API 格式)
NANOBANANA_API_KEY=sk-...
# NANOBANANA_BASE_URL=https://autorouter.io

# Backup: GPT-Image-2 (Chat Completions 格式)
OPENAI_API_KEY=sk-...
# OPENAI_BASE_URL=https://autorouter.io/v1

# ── 代理 ──
# HTTPS_PROXY=http://127.0.0.1:7890
```

## 认证体系

| 认证方式 | 用途 | 配置 |
|----------|------|------|
| OAuth 1.0a (User Context) | 发帖/删除/点赞/搜索/用户操作 | 4件套 |
| Bearer Token (App-Only) | 趋势/公开接口 | X_BEARER_TOKEN |

## 人格来源

### 1. 交互式创建 (推荐)
```bash
python -m src persona-custom
# 逐步输入: 名称 → 描述 → 关键词 → 语气 → 话题
# AI 生成完整人格画像
```

### 2. 蒸馏模式
```bash
# config.yaml 配置目标用户 → 爬取推文 → 分析风格
python -m src scrape
python -m src distill
```

## 图片生成链

```
nanobanana (Gemini API, 默认 nano-banana)
    ↓ 失败
GPT-Image-2 (Chat Completions)
    ↓ 失败
纯文本发布 (不阻断)
```

## 依赖

| 包 | 用途 |
|---|------|
| [xdk](https://pypi.org/project/xdk/) | X/Twitter 官方 Python SDK |
| [anthropic](https://pypi.org/project/anthropic/) | Claude API |
| openai | GPT-Image-2 + DALL-E |
| loguru | 日志 |
| aiosqlite | SQLite 异步访问 |
| croniter | Cron 调度 |
| httpx | HTTP 客户端 (nanobanana 调用等) |

## X API 层级说明

X API v2 采用付费制，部分接口需要付费层级：

| 接口 | 最低层级 | 说明 |
|------|----------|------|
| `posts.create` (发帖) | Free | OAuth 1.0a User Context |
| `users.get_me` (自己的信息) | Free | OAuth 1.0a |
| `trends.get_by_woeid` (趋势) | Free (App-Only) | Bearer Token |
| `users.get_by_username` (查询用户) | Basic ($100/月) | 402 表示需升级 |
| `posts.search_recent` (搜索) | Basic ($100/月) | 402 表示需升级 |

> 当前账户为 Free 层级，发帖/趋势/自己信息可用。爬取和搜索需升级至 Basic。

## 测试

```bash
# 图片生成 API 测试
python tests/test_image_api.py

# 用户查询 API 测试
python tests/test_users.py
```

## 参考链接

- XDK Python SDK 模块参考: https://docs.x.com/xdks/python/reference/modules
- XDK 认证文档: https://docs.x.com/xdks/python/authentication
- X Developer Portal: https://developer.x.com/en/portal/dashboard
- X API 层级定价: https://developer.x.com/en/portal/products
