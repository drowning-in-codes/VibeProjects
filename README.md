# VibeProjects

个人项目集合。

## 项目列表

| 项目 | 说明 | 技术栈 |
|---|---|---|
| [EasyTwit](./EasyTwit/) | X/Twitter AI 自动发帖 — 爬取推文 → 蒸馏人格 → 自动发推 | Python, XDK, Claude API, SQLite, Docker |
| [bili-live-report](./bili-live-report/) | B站直播日报自动推送系统 (新版) | Python, bilibili-api, jieba, wordcloud, PushPlus |
| [biliLiveSummary](./biliLiveSummary/) | B站直播日报自动推送系统 (旧版) | Python, bilibili-api, SQLite |
| [simpleMusic](./simpleMusic/) | 现代音乐网站 — 在线音乐播放、歌单管理 | Spring Boot 3, MyBatis, MySQL, Vue 3, Element Plus |
| [smart-campus](./smart-campus/) | 高校在线学习平台 — 课程、考试、学习管理 | Spring Boot, MyBatis, MySQL, Vue 3 |
| [wechat_article_explorer](./wechat_article_explorer/) | 微信读书公众号文章浏览与导出扩展 — 搜索、批量拉取、筛选和导出公众号文章 | Chrome/Edge MV3, JavaScript, 微信读书接口 |

---

### EasyTwit

基于 **XDK Python SDK** + **OAuth 1.0a** 的 X/Twitter 自动发帖应用。爬取推文 → AI 蒸馏人格 → 用人格自动发推，支持知乎数据源作为生成上下文、图片配图、数据追踪与互动增长。

```
EasyTwit/
├── src/
│   ├── main.py               # CLI 入口 + 命令路由
│   ├── config.py             # YAML + .env 配置
│   ├── poster.py             # 推文发布整合
│   ├── scheduler.py          # Cron 定时调度
│   ├── x/                    # X/Twitter 模块 (client, scraper, auth)
│   ├── ai/                   # AI 模块 (persona, generator, image, fallback)
│   ├── zhihu/                # 知乎数据源 (热榜/搜索/直答AI)
│   └── storage/              # SQLite 持久化 (Tweet, Persona, PostHistory)
├── personas/                 # 18 个人格模板 (tech/social/career/finance)
├── prompts/                  # Prompt 模板 (viral/professional/casual)
├── tests/
├── Dockerfile / docker-compose.yml
├── config.yaml / .env.example / requirements.txt
└── README.md
```

| 命令 | 说明 |
|---|---|
| `python -m src auth` | OAuth 1.0a 浏览器认证 |
| `python -m src setup` | 初始化数据库和目录 |
| `python -m src scrape -u username` | 爬取用户推文 |
| `python -m src distill` | 从推文蒸馏人格 |
| `python -m src persona-custom` | 交互式创建人格 |
| `python -m src generate -t topic` | 生成推文预览 |
| `python -m src post -t topic` | 发布推文 (过长自动 thread) |
| `python -m src pipeline` | 完整流程: 爬取→蒸馏→发帖 |
| `python -m src run` | 定时调度 (完整 pipeline) |
| `python -m src run --easy` | 轻量调度 (随机人格→发帖) |
| `python -m src trends` | 全球趋势 |
| `python -m src analytics` | 数据看板 |
| `python -m src engage` | 互动增长 |
| `python -m src status` | 查看状态 |

---

### biliLiveSummary

每日自动采集B站关注UP主的直播信息（标题、弹幕词云、AI总结），通过 PushPlus 推送到微信。

```
biliLiveSummary/
├── main.py              # CLI 入口 (login/watch/run/schedule)
├── config.yaml          # 用户配置
├── src/
│   ├── auth.py          # 扫码/cookie登录
│   ├── collector.py     # 直播+弹幕采集
│   ├── analyzer.py      # 词云+AI总结
│   ├── notifier.py      # PushPlus推送
│   └── storage.py       # YAML+SQLite存储
└── requirements.txt
```

---

### bili-live-report

B站直播日报系统 **重写版**，架构更完整。定时采集关注UP主的直播数据，生成弹幕词云 + AI 内容总结，通过 PushPlus 多渠道推送。

```
bili-live-report/
├── src/
│   ├── config.py         # YAML + .env 配置管理
│   ├── bilibili/         # B站 API 模块 (直播/弹幕/用户)
│   ├── analysis/         # 分析模块 (词云/AI总结)
│   ├── push/             # PushPlus 推送模块
│   └── storage/          # 持久化模块
├── data/                 # 数据目录 (session, following, history)
├── output/               # 输出目录 (词云图片)
├── logs/                 # 日志目录
├── config.yaml           # 用户配置 (AI模型/B站/PushPlus/调度)
├── requirements.txt
└── .env.example
```

---

### simpleMusic

功能完整的现代音乐网站，前后端分离架构。提供音乐播放（增强播放器含歌词同步）、歌单管理、用户注册登录、播放历史记录等功能。MVP 聚焦用户端核心体验，管理端预留第二期。

```
simpleMusic/
├── simpleMusic-backend/          # Spring Boot 3.x + Java 21 (Maven 多模块)
│   ├── simpleMusic-common/       # 公共模块 (PO/DTO/VO/Service/Mapper)
│   ├── simpleMusic-web/          # 用户端 API (端口 6060, context-path: /api)
│   └── simpleMusic-admin/        # 管理端 API (预留)
├── simpleMusic-front/            # Vue 3 + Vite + Element Plus
│   ├── simpleMusic-front-web/    # 用户端前端
│   └── simpleMusic-front-admin/  # 管理端前端 (第二期)
└── README.md
```

**后端**: Spring Boot 3.5.4, MyBatis 3.0.5, MySQL 8.3, Redis, JWT, Lombok, Logback
**前端**: Vue 3.5, Vue Router 5, Pinia 3, Element Plus, Axios

---

### smart-campus

高校在线学习平台，前后端分离，后端拆分为管理端 + 用户端两个独立服务，各自带独立拦截器与登录态。

```
smart-campus/
├── smart-campus-backend/         # Spring Boot (Maven 多模块)
│   ├── smart-campus-common/      # 公共模块 (PO/DTO/VO/Mapper/Redis/Exception)
│   ├── smart-campus-admin/       # 管理端服务 (管理员+教师)
│   └── smart-campus-web/         # 用户端服务 (学生)
├── smart-campus-front/           # Vue 3 前端
│   ├── smart-campus-front-admin/ # 管理后台
│   └── smart-campus-front-web/   # 学生端
└── CLAUDE.md
```

**核心业务**: 基础数据（院系/专业/班级/用户）、教学（课程→章节→课时→资源）、习题试卷、在线考试、作业评估、学习数据追踪、资源管理、系统权限

**技术栈**: Spring Boot, MyBatis, MySQL, Redis, Vue 3, JWT 认证

---

### wechat_article_explorer

Chrome / Edge Manifest V3 浏览器扩展，用于在微信读书网页版或微信公众号页面中管理和查看公众号文章。扩展通过微信读书接口读取文章，支持按公众号批量拉取、筛选和导出，不需要单独部署后端服务。

**主要功能**:

- 刷新微信读书关注的公众号，并添加到文章查看列表；
- 按公众号名称搜索，或通过文章链接、`__biz`、`fakid`、`MP_WXS_数字` 添加公众号；
- 在公众号文章页面识别当前公众号，一键收录公众号或文章；
- 按公众号分组查看文章，支持关键词和日期筛选；
- 每个公众号默认显示 3 篇文章，可按需逐步显示更多；
- 导出 CSV、Markdown，复制文章链接或标题+链接；
- 支持深色/浅色模式和本地缓存；
- 提供诊断导出，方便排查接口字段变化。

```text
wechat_article_explorer/
├── manifest.json    # Manifest V3 配置、权限和注入入口
├── content.js       # 页面注入、界面和主要业务逻辑
├── content.css      # 抽屉、列表和主题样式
├── background.js    # 跨域请求及标签页代理
└── README.md        # 安装、使用和贡献说明
```

**使用方式**:

1. 在 Chrome 或 Edge 的扩展管理页面开启开发者模式；
2. 选择“加载已解压的扩展程序”，加载 `wechat_article_explorer` 目录；
3. 打开 `weread.qq.com` 或 `mp.weixin.qq.com`；
4. 打开页面右侧的“公众号导出”抽屉，登录微信读书后添加公众号并拉取文章。

公众号名称搜索需要公众号后台登录态；文章读取需要微信读书登录态。详细安装步骤、权限说明、常见问题和接口限制见 [`wechat_article_explorer/README.md`](./wechat_article_explorer/README.md)。

## 参与贡献

欢迎通过 Issue 和 Pull Request 参与改进：

- 报告可复现的 Bug、接口变化或浏览器兼容性问题；
- 改进项目功能、交互、样式、错误提示和文档；
- 补充测试、诊断工具或其他浏览器支持；
- 分享不包含敏感信息的接口变化和兼容方案。

提交前建议：

1. 一个 Pull Request 尽量只解决一个问题；
2. 同步更新受影响项目的 README；
3. 运行对应项目已有的检查命令；
4. 在描述中说明修改原因、测试方式和已知限制；
5. 不要提交 Cookie、Token、密码、二维码、个人账号信息或本地缓存。

对于 `wechat_article_explorer`，可在项目目录运行：

```powershell
node --check content.js
node --check background.js
Get-Content manifest.json | ConvertFrom-Json | Out-Null
git diff --check
```

提交 Issue 或诊断文件前，请先脱敏登录凭据、Token、Cookie 及文章中的个人信息。
