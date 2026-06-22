# API Base URL 自定义配置指南

## 🌐 为什么需要自定义 Base URL？

### 使用场景

1. **使用代理服务** - 国内访问 OpenAI/Anthropic 需要代理
2. **使用第三方兼容服务** - 如 Azure OpenAI、OneAPI 等
3. **企业内网环境** - 通过内部网关访问 API
4. **成本优化** - 使用更便宜的兼容服务

---

## ⚙️ 配置方式

### Anthropic API Base URL

编辑 `.env` 文件：

```bash
# 标准配置
ANTHROPIC_API_KEY=sk-ant-xxx

# 自定义 Base URL（可选）
ANTHROPIC_BASE_URL=https://your-proxy.com/v1
```

**默认值**: `https://api.anthropic.com`

### OpenAI API Base URL

```bash
# 标准配置
OPENAI_API_KEY=sk-proj-xxx

# 自定义 Base URL（可选）
OPENAI_BASE_URL=https://your-proxy.com/v1
```

**默认值**: `https://api.openai.com/v1`

---

## 🔧 常见配置示例

### 1. 使用 OpenAI 代理

```bash
# .env
OPENAI_API_KEY=sk-proj-xxx
OPENAI_BASE_URL=https://api.openai-proxy.com/v1
```

### 2. 使用 Azure OpenAI

```bash
OPENAI_API_KEY=your-azure-key
OPENAI_BASE_URL=https://your-resource.openai.azure.com/
```

### 3. 使用 OneAPI 中转

```bash
# OneAPI 部署在 https://oneapi.example.com
OPENAI_API_KEY=sk-xxx  # OneAPI 生成的 key
OPENAI_BASE_URL=https://oneapi.example.com/v1

ANTHROPIC_API_KEY=sk-ant-xxx  # OneAPI 生成的 key
ANTHROPIC_BASE_URL=https://oneapi.example.com/v1
```

### 4. 使用 Cloudflare AI Gateway

```bash
OPENAI_API_KEY=sk-proj-xxx
OPENAI_BASE_URL=https://gateway.ai.cloudflare.com/v1/YOUR_ACCOUNT_ID/YOUR_GATEWAY/openai
```

### 5. 使用本地部署的兼容服务

```bash
# 本地 LiteLLM 代理
OPENAI_API_KEY=sk-xxx
OPENAI_BASE_URL=http://localhost:8000/v1

ANTHROPIC_API_KEY=sk-ant-xxx
ANTHROPIC_BASE_URL=http://localhost:8000/v1
```

---

## ✅ 验证配置

### 测试 Anthropic 连接

```bash
# 测试爬取和分析功能
python main.py crawl elonmusk 10
python main.py analyze elonmusk
```

**预期输出**:
```
[INFO] 使用自定义 Anthropic API: https://your-proxy.com/v1
[INFO] 开始分析 @elonmusk 的人格特征
...
```

### 测试 OpenAI 连接

```bash
# 测试图片生成功能
python main.py generate "人工智能"
```

**预期输出**:
```
[INFO] 使用自定义 OpenAI API: https://your-proxy.com/v1
[INFO] 使用 DALL-E-3 生成图片...
...
```

---

## 🐛 故障排查

### 问题 1: 连接超时

**症状**:
```
Error: Connection timeout
```

**解决方案**:
1. 检查 Base URL 是否正确
2. 确认代理服务是否可访问
3. 测试网络连接：`curl https://your-proxy.com/v1/models`

### 问题 2: 401 Unauthorized

**症状**:
```
Error: 401 Unauthorized
```

**解决方案**:
1. 检查 API Key 是否正确
2. 确认代理服务是否需要特殊的 Key 格式
3. 查看代理服务文档

### 问题 3: 404 Not Found

**症状**:
```
Error: 404 Not Found
```

**解决方案**:
1. 检查 Base URL 路径是否完整
2. OpenAI 需要 `/v1` 后缀
3. Anthropic 不需要 `/v1` 后缀

### 问题 4: 模型不兼容

**症状**:
```
Error: Model 'claude-opus-4-6' not found
```

**解决方案**:
编辑 `config.yaml`，使用代理支持的模型：
```yaml
anthropic:
  model: "claude-3-opus-20240229"  # 旧版模型名
```

---

## 🔒 安全建议

### 1. 不要泄露 API Key
```bash
# ❌ 错误：直接写在代码里
api_key = "sk-proj-xxxxx"

# ✅ 正确：使用环境变量
api_key = os.getenv("OPENAI_API_KEY")
```

### 2. 使用 HTTPS
```bash
# ❌ 不安全
OPENAI_BASE_URL=http://your-proxy.com/v1

# ✅ 安全
OPENAI_BASE_URL=https://your-proxy.com/v1
```

### 3. 定期轮换密钥
```bash
# 每 30-90 天更换一次 API Key
```

---

## 📊 代理服务对比

### OneAPI（推荐）
- ✅ 开源免费
- ✅ 支持多种 AI 模型
- ✅ 统一 API 接口
- ✅ 流量监控和限额
- 🔗 https://github.com/songquanpeng/one-api

### LiteLLM
- ✅ Python 原生
- ✅ 100+ 模型支持
- ✅ 负载均衡和重试
- 🔗 https://github.com/BerriAI/litellm

### Cloudflare AI Gateway
- ✅ CDN 加速
- ✅ 缓存优化
- ✅ 分析面板
- 💰 免费额度
- 🔗 https://ai.cloudflare.com

### Azure OpenAI
- ✅ 企业级稳定性
- ✅ 数据隐私保护
- 💰 按需付费
- 🔗 https://azure.microsoft.com/en-us/products/ai-services/openai-service

---

## 🎯 最佳实践

### 1. 优先使用官方 API
```bash
# 除非必要，优先使用官方 API
# 不设置 BASE_URL = 使用官方默认
```

### 2. 测试环境先验证
```bash
# 先在测试环境验证代理可用
python main.py generate "测试" --dry-run
```

### 3. 监控日志
```bash
# 观察是否有 "使用自定义 API" 的日志
tail -f logs/autotwit.log | grep "自定义"
```

### 4. 备用方案
```bash
# 准备多个代理地址
OPENAI_BASE_URL=https://proxy1.com/v1  # 主
# OPENAI_BASE_URL=https://proxy2.com/v1  # 备
```

---

## 💡 高级配置

### 多环境配置

```bash
# .env.production（生产环境）
OPENAI_BASE_URL=https://api.openai.com/v1

# .env.development（开发环境）
OPENAI_BASE_URL=http://localhost:8000/v1

# .env.china（国内环境）
OPENAI_BASE_URL=https://openai-proxy.cn/v1
ANTHROPIC_BASE_URL=https://anthropic-proxy.cn/v1
```

### 使用不同配置

```bash
# 加载不同环境配置
cp .env.production .env  # 生产
# 或
cp .env.china .env       # 国内

python main.py start
```

---

## 📞 获取帮助

### 代理服务不工作？
1. 检查 Base URL 格式
2. 测试 API 连接：`curl -H "Authorization: Bearer $OPENAI_API_KEY" $OPENAI_BASE_URL/models`
3. 查看代理服务日志

### 模型不可用？
1. 确认代理支持的模型列表
2. 修改 `config.yaml` 中的模型名称
3. 参考代理服务文档

### 性能问题？
1. 使用地理位置近的代理
2. 启用 CDN 加速
3. 考虑使用 Cloudflare AI Gateway

---

## 🎉 配置完成

配置好 Base URL 后，系统将自动使用自定义端点，无需修改其他代码。

**启动系统**:
```bash
python main.py start
```

**查看日志确认**:
```bash
tail -f logs/autotwit.log
# 应该看到 "使用自定义 Anthropic/OpenAI API" 的日志
```
