# autoTwit - X/Twitter 自动化系统

基于 XActions 和 AI 的 X/Twitter 自动化发帖、爬取、人格蒸馏系统。支持从 X/Twitter 和知乎双平台蒸馏人格特征，生成 SKILL.md 供 AI 模仿写作风格。

## 功能特性

### 核心功能
- ✅ **自动爬取推文** — 定时爬取目标用户推文并存储
- ✅ **AI 人格蒸馏** — Claude 分析推文/知乎内容，提取写作风格
- ✅ **智能内容生成** — 基于人格特征生成符合风格的推文
- ✅ **智能配图判断** — 根据内容类型自动决定是否配图（节省 30-50% 成本）
- ✅ **双层图片生成** — Claude 分析推文 → 提取视觉元素 → DALL-E 生成
- ✅ **自动发布** — 定时发布文本+图片推文
- ✅ **CLI 全功能** — 命令行控制所有操作

### 知乎集成
- ✅ **知乎搜索** — 站内搜索 + 全网搜索（global_search）
- ✅ **知乎直答** — 集成 zhida-fast/thinking/agent 三个模型
- ✅ **知乎人格蒸馏** — 搜索/收集内容 → AI 分析 → 生成 SKILL.md
- ✅ **批量蒸馏** — 按作者聚合，一次搜索生成多个 SKILL.md
- ✅ **深度分析** — 支持两轮精炼（特征提取 + 风格深化）

### 成本控制
- ✅ **DALL-E 2/3 双模式** — $0.02/张 ~ $0.12/张自由选择
- ✅ **自定义 API 端点** — 支持代理、OneAPI、Azure 等中转
- ✅ **三级图片降级** — 本地图库 → Unsplash → DALL-E

---

## 技术栈

| 层级 | 技术 | 用途 |
|------|------|------|
| 语言 | Python 3.11+ | 主程序 |
| 语言 | Node.js 18+ | XActions 桥接 |
| X 自动化 | XActions 3.x | 无需 X 官方 API |
| AI 分析 | Claude Opus/Sonnet | 人格蒸馏 & 内容生成 |
| AI 配图 | DALL-E 2/3 | 图片生成 |
| AI 备选 | 知乎直答 | zhida-thinking 模型 |
| 数据库 | SQLite | 本地持久化 |
| 调度 | APScheduler | 定时任务 |
| 图片 | Pillow + Unsplash | 图片处理 & 备选图源 |
| 数据源 | 知乎开放平台 | 搜索 & 直答 API |

---

## 快速开始

### 1. 环境要求

- Python 3.11+
- Node.js 18+
- X/Twitter 账号

### 2. 安装

```bash
pip install -r requirements.txt
npm install
```

### 3. 配置

```bash
cp .env.example .env
```

编辑 `.env` 填入关键配置：

```env
# 必需
X_AUTH_TOKEN=your_auth_token_here
ANTHROPIC_API_KEY=sk-ant-xxx

# 可选 — 图片生成
OPENAI_API_KEY=sk-proj-xxx

# 可选 — API 代理
ANTHROPIC_BASE_URL=https://your-proxy.com/v1
OPENAI_BASE_URL=https://your-proxy.com/v1

# 可选 — 知乎
ZHIHU_ACCESS_SECRET=your_access_secret
```

编辑 `config.yaml` 设置目标和模型：

```yaml
targets:
  users:
    - username: "elonmusk"
      enabled: true

zhihu:
  enabled: true
  chat_model: "thinking"
```

### 4. 测试

```bash
# 爬取推文
python main.py crawl elonmusk 50

# 分析人格
python main.py analyze elonmusk

# 生成推文（智能配图）
python main.py generate "AI 技术"
```

---

## 使用方法

### 定时任务

```bash
python main.py start
```

每天凌晨 2 点爬取目标用户推文 → 蒸馏人格 → 每 4 小时生成并发布一条推文。

### X/Twitter 操作

```bash
python main.py crawl <username> [count]        # 爬取推文
python main.py analyze <username>              # 分析人格特征
python main.py generate [topic] [image_mode]   # 生成推文
python main.py post "<content>" [image]        # 发布推文
```

`image_mode`:
- `auto` — 智能判断（默认，推荐）
- `yes` — 强制配图
- `no` — 强制无图

### 知乎操作

```bash
# 搜索内容
python main.py zhihu search "人工智能" 30

# 蒸馏用户人格 → 生成 SKILL.md
python main.py zhihu user zhang-jia-wei 50

# 批量蒸馏
python main.py zhihu distill "创业" 50

# 直答对话
python main.py zhihu chat "什么是 AI Agent" thinking
```

蒸馏生成的 `SKILL.md` 保存在 `./skills/` 目录，可作为 AI 写作风格参考。

---

## 项目结构

```
autoTwit/
├── src/
│   ├── xactions/              # X/Twitter 自动化
│   │   ├── client.py          # XActions 封装
│   │   ├── scraper.py         # 推文爬取
│   │   └── automator.py       # 发帖/点赞/关注
│   ├── ai/                    # AI 模块
│   │   ├── persona.py         # X 推文人格蒸馏
│   │   ├── generator.py       # 内容生成 + 智能配图判断
│   │   ├── image.py           # 图片生成 (DALL-E 2/3)
│   │   └── image_prompt_optimizer.py  # 视觉元素提取
│   ├── zhihu/                 # 知乎集成
│   │   ├── client.py          # API 客户端 (搜索 + 直答)
│   │   ├── scraper.py         # 内容爬取器
│   │   └── persona.py         # 人格蒸馏 → SKILL.md
│   ├── storage/               # 数据持久化
│   │   ├── models.py          # 数据模型
│   │   └── database.py        # SQLite 操作
│   ├── scheduler/             # 定时任务
│   │   └── tasks.py           # APScheduler 编排
│   └── config.py              # 配置管理
├── skills/                    # 生成的 SKILL.md 文件
├── data/                      # 数据库文件
├── logs/                      # 日志
├── docs/                      # 详细文档
├── config.yaml                # 主配置
├── .env.example               # 环境变量模板
├── main.py                    # CLI 入口
└── README.md
```

---

## 工作流程

### X/Twitter 人格蒸馏

```
爬取推文 → Claude 分析 → 提取特征 → 保存 Persona
```

提取：语气风格、高频词汇、话题偏好、正式度、幽默感、技术深度

### 知乎人格蒸馏

```
搜索/收集内容 → Claude/直答分析 → 两轮精炼 → 生成 SKILL.md
```

SKILL.md 包含：人格画像、风格指标、写作模式、高频词汇、原文示例、模仿指南

### 智能内容生成

```
读取 Persona → 构建风格 Prompt → Claude 生成推文 → 智能配图判断 → DALL-E 配图
```

### 配图智能判断逻辑

1. 长度 < 40 字 → 无图
2. 科技/产品/教程关键词 → 配图
3. 问候/纯观点关键词 → 无图
4. 描述性词汇 → 配图
5. > 80 字 → 默认配图

详见：[SMART_IMAGE_LOGIC.md](docs/SMART_IMAGE_LOGIC.md)

---

## 配置参考

### config.yaml

```yaml
# XActions
xactions:
  cli_path: "./XActions/cli.js"

# AI
anthropic:
  model: "claude-opus-4-6"
  max_tokens: 2000

# 调度
scheduler:
  crawl_cron: "0 2 * * *"
  post_interval_hours: 4

# 目标用户
targets:
  users:
    - username: "elonmusk"
      enabled: false

# 图片生成
image:
  enabled: true
  provider: "dalle"
  dalle:
    model: "dall-e-3"
    size: "1024x1024"
    quality: "standard"

# 知乎
zhihu:
  enabled: false
  chat_model: "fast"
  search_queries:
    - "人工智能"

# 日志
logging:
  level: "INFO"
  file: "./logs/autotwit.log"
```

### .env 关键配置

| 变量 | 必需 | 说明 |
|------|------|------|
| `X_AUTH_TOKEN` | ✅ | X/Twitter 认证 Token |
| `ANTHROPIC_API_KEY` | ✅ | Claude API Key |
| `OPENAI_API_KEY` | 图片 | DALL-E 图片生成 |
| `ZHIHU_ACCESS_SECRET` | 知乎 | 知乎开放平台 Bearer Token |
| `ANTHROPIC_BASE_URL` | 代理 | Anthropic API 中转地址 |
| `OPENAI_BASE_URL` | 代理 | OpenAI API 中转地址 |

---

## 成本估算

| 方案 | 模型 | 图片 | 月成本 |
|------|------|------|--------|
| 入门 | Sonnet 4.6 | DALL-E 2 | ~$3-5 |
| 标准 | Opus 4.6 | DALL-E 3 | ~$10-15 |
| 专业 | Opus 4.6 | DALL-E 3 HD | ~$20-30 |
| 商业 | Opus 4.6 + zhida-thinking | DALL-E 3 HD | ~$40-60 |

智能配图判断可额外节省 30-50% 图片费用。

---

## 注意事项

### 账号安全
- 每 4 小时发一条较安全
- 使用小号先测试
- auth_token 定期更新

### API 费用
- Claude Opus: $15/$75 每百万 tokens
- Claude Sonnet: $3/$15 每百万 tokens
- DALL-E 2: $0.02/张 | DALL-E 3: $0.04/张 (standard) / $0.08/张 (HD)

### 法律合规
- 仅用于学习和研究
- 遵守 X/Twitter 服务条款
- 不用于垃圾信息和侵权

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [QUICKSTART.md](QUICKSTART.md) | 5 分钟快速开始 |
| [docs/IMAGE_GENERATION.md](docs/IMAGE_GENERATION.md) | 图片生成完整指南 |
| [docs/SMART_IMAGE_LOGIC.md](docs/SMART_IMAGE_LOGIC.md) | 智能配图判断逻辑 |
| [docs/DALLE_COMPARISON.md](docs/DALLE_COMPARISON.md) | DALL-E 2/3 对比 |
| [docs/API_BASE_URL.md](docs/API_BASE_URL.md) | API 代理配置 |

---

## 后续扩展

- [ ] Web 控制面板
- [ ] 多账号管理
- [ ] 自动回复评论
- [ ] 跨平台支持（Bluesky/Mastodon）
- [ ] 话题趋势分析
- [ ] A/B 测试系统

---

## 开源协议

MIT License

---

**免责声明**: 本项目仅供学习和研究使用，使用者需自行承担使用本工具的风险和责任。
