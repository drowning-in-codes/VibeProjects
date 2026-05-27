# LLM API 方案对比

## Token 消耗估算

假设：每天 30 场直播，每场 5000 输入 tokens（弹幕样本 + 标题等） + 400 输出 tokens（摘要）
- 月均：~5M 输入 + ~0.4M 输出 tokens

## 成本排名（月均，人民币）

| 排名 | 方案 | 月成本 | 需要翻墙 | 中文质量 |
|---|---|---|---|---|
| 1 | Qwen-Turbo (通义千问) | ~1.9 元 | 否 | ⭐⭐⭐⭐ |
| 2 | DeepSeek-V3 | ~5.8 元 | 否 | ⭐⭐⭐⭐⭐ |
| 3 | GPT-4o-mini | ~7.1 元 | 是 | ⭐⭐⭐⭐ |
| 4 | 本地 Ollama + Qwen2.5-7B | 0 元(需GPU≥6GB) | 否 | ⭐⭐⭐ |
| 5 | Claude Haiku 4.5 | ~5 元 | 是 | ⭐⭐⭐ |

## 各方案详情

### DeepSeek-V3 (推荐)
- API: `api.deepseek.com/v1`，兼容 OpenAI SDK
- 价格: 输入 ¥1/1M tokens, 输出 ¥2/1M tokens
- 优势: 中文理解最深，对B站梗/网络用语理解好，国内直接访问
- 风险: 高峰期偶有限流，需加重试

### Qwen-Turbo (备选)
- API: `dashscope.aliyuncs.com`，兼容 OpenAI SDK
- 价格: 输入 ¥0.3/1M tokens, 输出 ¥0.6/1M tokens
- 优势: 最便宜，阿里云基础设施稳定，新用户大量免费额度

### 本地 Ollama + Qwen2.5-7B (白嫖方案)
- 需要: GPU ≥ 6GB VRAM，或 CPU 16GB+ 内存
- 优势: 零成本，隐私，无需网络
- 劣势: 质量不如云端模型，速度取决于硬件

## 推荐

**首选 DeepSeek-V3**: 中文最好 + 月均不到6元 + 不用翻墙 + 兼容 OpenAI SDK
**备选 Qwen-Turbo**: 更便宜，更稳定
**白嫖**: 本地 Ollama，跑通流程后随时切云端

## Prompt 设计要点

- System prompt 需指定角色: "你是B站直播内容分析师，擅长从弹幕中提取关键信息"
- 输入格式: 标题 + 弹幕样本(去重后最多500条) + 直播分区
- 输出格式: 3-5句话的摘要 + 3-5个关键词
