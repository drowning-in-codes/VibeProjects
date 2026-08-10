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
# 必填
ANTHROPIC_API_KEY=sk-ant-...          # Claude API
X_API_KEY=...                          # Consumer Key
X_API_SECRET=...                       # Consumer Secret
X_ACCESS_TOKEN=...                     # OAuth 1.0a Access Token
X_ACCESS_TOKEN_SECRET=...              # OAuth 1.0a Access Token Secret
# 可选
X_BEARER_TOKEN=...                     # 趋势接口
NANOBANANA_API_KEY=sk-...              # 图片生成 (主)
OPENAI_API_KEY=sk-...                  # 图片生成 (备)
```

或使用 OAuth 自动认证:
```bash
python -m src auth          # 浏览器授权 → 自动写入 .env
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

## CLI 命令

| 命令 | 说明 |
|------|------|
| `python -m src auth` | OAuth 1.0a 浏览器认证 |
| `python -m src setup` | 初始化数据库和目录 |
| `python -m src scrape -u username` | 按用户名爬取推文 |
| `python -m src scrape -f` | 爬取关注列表 |
| `python -m src scrape -t` | 爬取时间线 |
| `python -m src distill` | 从推文蒸馏人格 |
| `python -m src persona-custom` | 交互式创建人格 (逐步输入) |
| `python -m src persona-custom --config` | 从模板创建人格 |
| `python -m src generate -t topic` | 生成推文预览 |
| `python -m src post -t topic` | 发布推文 (过长自动 thread) |
| `python -m src pipeline` | 完整流程: 爬取→蒸馏→发帖 |
| `python -m src trends -w worldwide` | 全球趋势 |
| `python -m src analytics -d 30` | 数据看板 (曝光/点赞/互动率) |
| `python -m src engage` | 互动增长 (like Blue 用户帖子) |
| `python -m src run --now` | 定时调度 (启动即执行完整 pipeline) |
| `python -m src run --easy --now` | 轻量调度 (跳过爬取, 直接随机人格→发帖) |
| `python -m src status` | 查看状态 |

## 项目结构

```
EasyTwit/
├── src/
│   ├── main.py               # CLI 入口 + 命令路由
│   ├── config.py             # YAML + .env 配置
│   ├── poster.py             # 推文发布整合
│   ├── scheduler.py          # Cron 定时调度
│   ├── x/                    # X/Twitter 模块
│   │   ├── client.py         # XDK 客户端
│   │   ├── scraper.py        # 推文爬取器
│   │   └── auth.py           # OAuth 三步认证
│   ├── ai/                   # AI 模块
│   │   ├── persona.py        # 人格蒸馏 + 模板加载
│   │   ├── generator.py      # 推文生成 + Prompt 模板
│   │   ├── image.py          # nanobanana + GPT-Image-2
│   │   └── fallback.py       # API 主备切换
│   ├── zhihu/                # 知乎数据源
│   │   └── client.py         # 热榜/搜索/直答 AI
│   └── storage/              # 持久化
│       ├── models.py         # Tweet / Persona / PostHistory
│       └── database.py       # SQLite
├── personas/                 # 人格模板 (按组分类)
│   ├── tech/                 # 科技组
│   │   ├── tech-blogger.yaml
│   │   ├── tech-discussant.yaml
│   │   ├── dev-insider.yaml
│   │   └── hot-tech-tracker.yaml     🔗 知乎
│   ├── social/               # 社交组
│   │   ├── casual-observer.yaml
│   │   ├── gen-z-trendy.yaml
│   │   ├── life-observer.yaml
│   │   ├── hot-topic-debater.yaml    🔗 知乎
│   │   ├── meme-writer.yaml
│   │   ├── story-writer.yaml
│   │   ├── anecdote-teller.yaml
│   │   ├── daily-life.yaml
│   │   └── blue-promoter.yaml
│   ├── career/               # 职场组
│   │   ├── career-survivor.yaml
│   │   └── career-hot-watcher.yaml   🔗 知乎
│   ├── finance/              # 财经组
│   │   ├── market-analyst.yaml
│   │   ├── news-interpreter.yaml     🔗 知乎
│   │   └── investment-guru.yaml      🔗 知乎
│   └── {username}.yaml       # distill 蒸馏自动生成
├── prompts/                  # Prompt 模板目录
│   ├── viral.md
│   ├── professional.md
│   └── casual.md
├── tests/
│   ├── test_image_api.py
│   ├── test_users.py
│   └── test_scrape.py
├── Dockerfile / docker-compose.yml
├── config.yaml / .env.example / requirements.txt
└── README.md
```

## 配置

### config.yaml

```yaml
targets:
  scrape_source: users          # users | following | timeline
  users:                        # 目标用户 (scrape_source=users 时生效)
    - username: elonmusk
      enabled: false
  persona_group: random         # 人格组: random | tech | social | career | finance
  group_weights:                # 随机选组权重
    tech: 40
    career: 30
    social: 35
    finance: 30
  reference_tweet_count: 2      # 生成时带入的参考推文数

anthropic:
  model: deepseek-v4-pro
  max_tokens: 2000
  generation_retries: 3         # 生成内容为空时重试次数
  system_prompt: "你是..."      # AI 角色定义，去 AI 味
  prompt_template: prompts/viral.md  # prompt 模板: viral | professional | casual | 留空

scheduler:
  run_immediately: true         # 启动时立即执行一次
  post_cron: "0 */4 * * *"     # 定时频率
  distill_cron: "0 0 */14 * *" # 蒸馏频率 (每两周)
  jitter_minutes: 30           # 时间扰动 ±30min
  max_posts_per_day: [1, 3]    # 每天随机在此范围内取值
  scrape_limit: 5
  following_limit: 5
  api_budget_per_day: 20       # API 日限额
  metrics_fetch_limit: 10
  engage_limit: 5              # 每日互动次数

nanobanana:
  model: nano-banana            # 图片生成模型 (主)

openai:
  model: gpt-image-2            # 图片生成模型 (备)

image:
  enabled: false
  output_dir: ./data/images
```

## 人格系统

### 模板方式 (推荐)

```bash
# 编辑或创建 personas/xxx.yaml, 然后在 config.yaml 中引用
persona_template: tech-blogger   # 固定模板
persona_template: random          # 随机选一个
persona_template:                 # 空 → 随机

# 从模板创建
python -m src persona-custom --config
```

模板格式 (`personas/tech-blogger.yaml`):

```yaml
name: 科技博主
description: 关注AI和科技前沿的理性思考者
keywords: [AI, 大模型, 开源, 第一性原理]
tone: 专业、理性、偶尔冷幽默
topics: [人工智能, 开源技术, 科技趋势]
```

### 交互方式

```bash
python -m src persona-custom
# 逐步输入: 名称 → 描述 → 关键词 → 语气 → 话题
```

### 蒸馏方式

```bash
python -m src scrape -u elonmusk   # 爬取推文
python -m src distill              # Claude 分析 → 人格
# 蒸馏后自动保存为 personas/{username}.yaml, 下次可随机复用
```

### 模板列表 (18个人格，4个组)

#### 💻 科技组 (tech)
| 文件 | 人格 | 风格 | 数据源 |
|------|------|------|--------|
| `tech-blogger.yaml` | 科技博主 | 理性分析，第一性原理 | - |
| `tech-discussant.yaml` | 技术讨论者 | 务实工程师，代码说话 | - |
| `dev-insider.yaml` | 开发者内行人 | 接地气，聊搞钱和生存 | - |
| `hot-tech-tracker.yaml` | 科技热点追踪者 | 信息密度高，像群友转发科技新闻 | 🔗 知乎 |

#### 💬 社交组 (social)
| 文件 | 人格 | 风格 | 数据源 |
|------|------|------|--------|
| `casual-observer.yaml` | 随性观察者 | 轻松生活化聊技术 | - |
| `gen-z-trendy.yaml` | 追热点年轻人 | 5G冲浪，玩梗吃瓜 | - |
| `life-observer.yaml` | 文科生活家 | 细腻温暖，观察人性 | - |
| `hot-topic-debater.yaml` | 热点争论者 | 犀利不失理性 | 🔗 知乎 |
| `meme-writer.yaml` | 梗文写手 | 幽默调侃，自嘲自黑 | - |
| `story-writer.yaml` | 故事写手 | 微小说叙事，情理之中意料之外 | - |
| `anecdote-teller.yaml` | 奇闻轶事讲述者 | 轻松聊天，引人入胜 | - |
| `daily-life.yaml` | 生活日常分享者 | 朋友圈式碎碎念，接地气 | - |
| `blue-promoter.yaml` | Blue增长推广员 | 互关引流，社区增长 | - |

#### 💼 职场组 (career)
| 文件 | 人格 | 风格 | 数据源 |
|------|------|------|--------|
| `career-survivor.yaml` | 职场老江湖 | 犀利务实，考公考研职场 | - |
| `career-hot-watcher.yaml` | 职场热点观察员 | 理性务实，不贩卖焦虑 | 🔗 知乎 |

#### 📈 财经组 (finance)
| 文件 | 人格 | 风格 | 数据源 |
|------|------|------|--------|
| `market-analyst.yaml` | 市场分析师 | 数据说话，概率思维 | - |
| `news-interpreter.yaml` | 新闻解读者 | 冷静客观，深挖事件脉络 | 🔗 知乎 |
| `investment-guru.yaml` | 投资老法师 | 实战派，聊美股/基金/复利 | 🔗 知乎 |

> 🔗 知乎 = 生成推文时会自动拉取知乎热榜/搜索数据作为实时上下文
>
> 蒸馏生成的人格 (`{username}.yaml`) 保存在 `personas/` 根目录

## Prompt 模板

`prompts/` 目录下的 `.md` 文件，在每次发帖前注入到 AI prompt 中：

| 文件 | 风格 |
|------|------|
| `viral.md` | 知乎/推特热度写法 |
| `professional.md` | 严谨专业 |
| `casual.md` | 随性日常 |

```yaml
# config.yaml
anthropic:
  prompt_template: prompts/viral.md  # 或留空跳过
```

## 图片生成链

```
nanobanana (Gemini API)
    ↓ 失败
GPT-Image-2 (Chat Completions)
    ↓ 失败
纯文本发布 (不阻断)
```

## 数据追踪 & 增长

### 数据看板 (P0)

```bash
python -m src analytics        # 最近 30 天数据
python -m src analytics -d 7   # 最近 7 天
```

追踪指标: 曝光量、点赞、转推、回复、互动率。自动拉取已发推文数据并汇总展示 500 万曝光进度。

### 互动增长 (P1)

```bash
python -m src engage           # 搜索 Blue 用户 → like 互动
```

搜索 "blue 互关" 等关键词，自动点赞相关推文，增加曝光和互关几率。

配置:
```yaml
scheduler:
  api_budget_per_day: 20      # API 日限额
  metrics_fetch_limit: 10     # 每次拉取数据条数
  engage_limit: 5             # 每日互动次数
```

## 调度器

```bash
python -m src run                 # 完整 pipeline: 爬取→蒸馏→发帖
python -m src run --easy          # 轻量模式: 随机人格→发帖 (不爬取不蒸馏)
python -m src run --easy --now    # 立即测试轻量模式
python -m src run --cron "*/30 * * * *"  # 自定义频率
```

## Docker 部署

```bash
docker build -t easytwit .
docker run --rm -v ./data:/app/data -v ./.env:/app/.env easytwit python -m src setup
docker run -it --rm -v ./.env:/app/.env -v ./data:/app/data easytwit python -m src persona-custom
docker compose up -d            # 后台定时调度
docker compose run --rm easytwit python -m src status
docker compose logs -f
```

## X API 层级

| 接口 | 层级 | 说明 |
|------|------|------|
| `posts.create` (发帖) | Free | OAuth 1.0a |
| `users.get_me` | Free | OAuth 1.0a |
| `trends.get_by_woeid` | Free | Bearer Token |
| `users.get_by_username` | Basic ($100/月) | 搜索/爬取需升级 |

## 知乎数据源

部分人格支持接入知乎平台数据作为生成上下文：

```yaml
# personas/social/hot-topic-debater.yaml
data_sources:
  - zhihu_hot                    # 知乎热榜
  - "zhihu_search: 热点新闻"     # 知乎搜索
  - "zhihu_global: 科技"         # 全网搜索
  - "zhida: 最新AI趋势"          # 知乎直答 AI

# 继承其他 persona 的数据源配置
inherit_data_sources: hot-topic-debater
```

配置 `.env`:

```bash
ZHIHU_ACCESS_SECRET=...    # 知乎开放平台 Access Secret
```

知乎 API 文档:

| 接口 | 文档 |
|------|------|
| 鉴权 | https://developer.zhihu.com/docs?key=authorization |
| 热榜 | https://developer.zhihu.com/docs?key=hot_list |
| 搜索 | https://developer.zhihu.com/docs?key=zhihu_search |
| 全网搜索 | https://developer.zhihu.com/docs?key=global_search |
| 直答 AI | https://developer.zhihu.com/docs?key=zhida |

## 测试

```bash
python tests/test_image_api.py
python tests/test_users.py
python tests/test_scrape.py
```

## 参考

- XDK 模块参考: https://docs.x.com/xdks/python/reference/modules
- XDK 认证: https://docs.x.com/xdks/python/authentication
- X Developer Portal: https://developer.x.com
- 知乎开放平台: https://developer.zhihu.com
