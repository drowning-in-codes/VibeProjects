# autoTwit - 快速入门指南

## 🚀 5 分钟快速开始

### 步骤 1: 克隆并安装依赖

```bash
cd autoTwit

# 安装 Python 依赖
pip install -r requirements.txt

# 安装 XActions (Node.js 依赖)
npm install
```

### 步骤 2: 配置 API Keys

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件
nano .env
```

**必需配置**:
```bash
# X/Twitter 认证 (从浏览器 Cookie 获取)
X_AUTH_TOKEN=your_auth_token_here

# Claude API (用于人格分析和内容生成)
ANTHROPIC_API_KEY=sk-ant-xxx
```

**可选配置** (用于图片生成):
```bash
# DALL-E 图片生成
OPENAI_API_KEY=sk-proj-xxx

# Unsplash 免费图库备选
UNSPLASH_ACCESS_KEY=xxx
```

### 步骤 3: 配置目标用户

编辑 `config.yaml`:
```yaml
targets:
  users:
    - username: "elonmusk"
      enabled: true    # 改为 true 启用
    - username: "naval"
      enabled: true
```

### 步骤 4: 测试运行

```bash
# 1. 爬取推文
python main.py crawl elonmusk 50

# 2. 分析人格
python main.py analyze elonmusk

# 3. 生成推文（带配图）
python main.py generate "人工智能"

# 4. 启动自动系统
python main.py start
```

---

## 📋 功能清单

### ✅ 已实现功能

- [x] **推文爬取** - 爬取目标用户推文并保存
- [x] **人格蒸馏** - Claude 分析推文风格，提取人格特征
- [x] **内容生成** - 基于人格特征生成推文
- [x] **智能配图** - Claude 分析推文 → DALL-E 生成配图
- [x] **自动发布** - 定时发布推文（文本+图片）
- [x] **手动操作** - CLI 工具支持手动操作
- [x] **数据持久化** - SQLite 存储所有数据

### 🎨 图片生成特性

- [x] **推文驱动** - 根据推文内容生成配图
- [x] **视觉分析** - Claude 提取视觉元素
- [x] **多提供者** - DALL-E / Unsplash / 本地图库
- [x] **智能降级** - 失败自动降级到备选方案
- [x] **成本控制** - 可配置质量和频率

---

## 🎯 典型使用场景

### 场景 1: 学习大佬风格自动发帖

```yaml
# config.yaml
targets:
  users:
    - username: "sama"        # Sam Altman
      enabled: true
    - username: "levelsio"    # Pieter Levels
      enabled: true

scheduler:
  crawl_cron: "0 2 * * *"     # 每天凌晨 2 点爬取
  post_interval_hours: 6      # 每 6 小时发一条
```

**效果**: 系统自动学习他们的风格，生成类似的推文并发布

---

### 场景 2: 品牌账号内容运营

```yaml
# 定制品牌风格
image:
  dalle:
    quality: "hd"             # 高质量配图

# 在代码中定制
BRAND_STYLE = "minimalist, startup aesthetic, pastel colors"
```

**效果**: 统一品牌调性的推文 + 配图

---

### 场景 3: 个人品牌建设

```bash
# 爬取行业 KOL
python main.py crawl pmarca 100   # Marc Andreessen
python main.py crawl naval 100    # Naval Ravikant

# 分析风格
python main.py analyze pmarca
python main.py analyze naval

# 生成你的推文
python main.py generate "Web3 的未来"
```

**效果**: 学习 KOL 风格，打造个人 IP

---

## 📊 工作流程图

```
┌─────────────────────────────────────────────────┐
│              autoTwit 系统架构                   │
└─────────────────────────────────────────────────┘

定时任务 1: 每日爬取
┌──────────────┐
│ 爬取目标用户  │
│  推文 (100条) │
└───────┬──────┘
        │
        ▼
┌──────────────┐      ┌──────────────┐
│   存入数据库  │─────▶│ Claude 分析   │
│  (tweets表)  │      │  提取人格特征  │
└──────────────┘      └───────┬──────┘
                              │
                              ▼
                      ┌──────────────┐
                      │   存入数据库  │
                      │ (personas表) │
                      └──────────────┘

定时任务 2: 自动发布
┌──────────────┐      ┌──────────────┐
│ 读取人格特征  │─────▶│  Claude 生成  │
│ (最新的 persona)│    │    推文文本   │
└──────────────┘      └───────┬──────┘
                              │
                              ▼
                      ┌──────────────┐
                      │ Claude 分析   │
                      │ 提取视觉元素  │
                      └───────┬──────┘
                              │
                              ▼
                      ┌──────────────┐
                      │ DALL-E 生成   │
                      │    配图       │
                      └───────┬──────┘
                              │
                              ▼
                      ┌──────────────┐
                      │  XActions    │
                      │  发布推文     │
                      └───────┬──────┘
                              │
                              ▼
                      ┌──────────────┐
                      │   发布成功    │
                      │  保存历史记录  │
                      └──────────────┘
```

---

## 💰 成本估算

### 方案 A: 最小成本（推荐入门）

```yaml
anthropic:
  model: "claude-sonnet-4-6"  # 更便宜

image:
  enabled: false              # 不生成图片

scheduler:
  post_interval_hours: 24     # 每天 1 条
```

**月成本**: ~$2-5 (仅 Claude API)

---

### 方案 B: 标准方案

```yaml
anthropic:
  model: "claude-opus-4-6"

image:
  enabled: true
  dalle:
    quality: "standard"

scheduler:
  post_interval_hours: 6      # 每天 4 条
```

**月成本**: ~$15-25
- Claude: ~$8-15
- DALL-E: ~$5-10 (120 张图)

---

### 方案 C: 高质量方案

```yaml
anthropic:
  model: "claude-opus-4-6"

image:
  enabled: true
  dalle:
    quality: "hd"

scheduler:
  post_interval_hours: 4      # 每天 6 条
```

**月成本**: ~$40-60
- Claude: ~$15-25
- DALL-E HD: ~$25-35 (180 张图)

---

## ⚠️ 重要提醒

### 账号安全
- ⚠️ **不要频繁操作**，容易触发 X 风控
- ⚠️ **建议测试账号**，不要用主号
- ⚠️ **每 4-6 小时发一条**较安全
- ⚠️ **auth_token 会过期**，定期更新

### API 使用
- 💰 **先设置小额预算**，避免意外扣费
- 📊 **监控 API 使用量**
- 🔑 **保护好 API Keys**，不要泄露

### 法律合规
- ✅ **仅用于学习研究**
- ✅ **遵守 X/Twitter 服务条款**
- ❌ **不要垃圾信息、骚扰、侵权**

---

## 🐛 常见问题

### Q1: auth_token 在哪里获取？
```
1. 登录 https://x.com
2. 打开浏览器开发者工具 (F12)
3. Application > Cookies > https://x.com
4. 找到 auth_token，复制值
```

### Q2: XActions 安装失败？
```bash
# 检查 Node.js 版本
node --version  # 需要 >= 18

# 重新安装
rm -rf node_modules package-lock.json
npm install
```

### Q3: DALL-E 生成图片失败？
```bash
# 检查 API Key
echo $OPENAI_API_KEY

# 检查余额
# https://platform.openai.com/usage

# 降级方案：禁用图片
# config.yaml: image.enabled: false
```

### Q4: Claude API 调用失败？
```bash
# 检查 API Key 是否正确
# 检查账户余额
# 检查网络连接
```

### Q5: 推文风格不像目标用户？
```bash
# 增加爬取推文数量
python main.py crawl <username> 200

# 重新分析人格
python main.py analyze <username>
```

---

## 📚 相关文档

- [IMAGE_GENERATION.md](./IMAGE_GENERATION.md) - 图片生成完整指南
- [IMAGE_DEMO.md](./IMAGE_DEMO.md) - 图片生成案例演示
- [README.md](../README.md) - 项目完整文档

---

## 🎓 下一步

1. ✅ **测试基础功能** - 爬取、分析、生成
2. ✅ **配置图片生成** - 设置 DALL-E API
3. ✅ **启动定时系统** - `python main.py start`
4. ✅ **监控日志** - 检查 `./logs/autotwit.log`
5. ✅ **优化风格** - 根据效果调整配置

---

**开始你的自动化推特之旅吧！🚀**

有问题？查看文档或提交 Issue。
