# 推文配图生成功能说明

## 🎨 核心思路

**推文内容 → AI 分析视觉元素 → 生成配图 → 发布**

不是"找图"，而是"为推文定制生成图片"。

---

## 🔄 完整工作流程

### 步骤 1: 生成推文文本
```python
content = "探索 AI 的未来：GPT-4 展示了惊人的推理能力，但 AGI 还有多远？"
```

### 步骤 2: Claude 分析推文 → 提取视觉元素
```json
{
  "main_subject": "未来感的人工智能大脑",
  "scene": "科技实验室，蓝色霓虹灯光",
  "style": "科幻风格，数字艺术",
  "mood": "神秘且振奋",
  "colors": ["深蓝", "紫色", "白色"],
  "elements": ["神经网络", "数据流", "电路板"],
  "avoid": ["文字", "人脸"]
}
```

### 步骤 3: 构建 DALL-E Prompt
```
A high-quality digital illustration for social media:

Main subject: 未来感的人工智能大脑
Scene: 科技实验室，蓝色霓虹灯光
Style: 科幻风格，数字艺术
Mood: 神秘且振奋
Color palette: 深蓝 and 紫色
Additional elements: 神经网络, 数据流, 电路板

Requirements:
- Professional and polished
- Suitable for Twitter/X post
- No text or words in the image
- 16:9 or square aspect ratio
- Avoid: 文字, 人脸
```

### 步骤 4: DALL-E 生成图片
```
./temp/dalle_xxxxx.png
```

### 步骤 5: 发布推文 + 图片
```python
await automator.post_tweet(content, image_path)
```

---

## 🚀 使用示例

### 方式 1: 自动生成（推荐）
```bash
# 定时任务会自动：生成推文 → 分析 → 生成图片 → 发布
python main.py start
```

### 方式 2: 手动生成预览
```bash
# 生成推文并预览（不发布）
python main.py generate "人工智能"

# 输出：
# 推文: "探索 AI 的未来..."
# 图片: ./temp/dalle_123456.png
```

### 方式 3: 自定义推文 + 生成配图
```python
# Python 代码示例
from src.ai.generator import ContentGenerator
from src.ai.image import ImageManager

# 生成推文（带图片）
content, image_path = await generator.generate_tweet(
    persona=persona,
    topic="区块链技术",
    with_image=True
)

# 发布
await automator.post_tweet(content, image_path)
```

---

## ⚙️ 配置选项

### config.yaml
```yaml
image:
  enabled: true                    # 是否启用图片生成
  provider: "dalle"                # dalle / stable-diffusion / midjourney
  fallback_to_unsplash: true       # DALL-E 失败时降级到 Unsplash
  
  dalle:
    model: "dall-e-3"
    size: "1024x1024"              # 1024x1024 / 1792x1024 / 1024x1792
    quality: "standard"            # standard / hd
    
  unsplash:
    enabled: true
    access_key_env: "UNSPLASH_ACCESS_KEY"
```

### .env
```bash
# OpenAI API Key (用于 DALL-E)
OPENAI_API_KEY=sk-proj-xxx

# Unsplash API Key (可选，备用方案)
UNSPLASH_ACCESS_KEY=xxx
```

---

## 💰 成本分析

### DALL-E 3 定价
- **Standard 质量 (1024x1024)**: $0.040/张
- **HD 质量 (1024x1024)**: $0.080/张

### 成本估算
| 发帖频率 | 月图片数 | 月成本 (Standard) | 月成本 (HD) |
|---------|---------|------------------|------------|
| 每 4 小时 | ~180 张 | $7.20 | $14.40 |
| 每天 1 次 | ~30 张 | $1.20 | $2.40 |
| 每周 3 次 | ~12 张 | $0.48 | $0.96 |

### 免费备选方案
1. **Unsplash** - 完全免费，但图片可能不够定制
2. **本地图库** - 提前准备图片，无成本
3. **Stable Diffusion (本地)** - 一次性配置成本，之后免费

---

## 🎯 三种图片生成模式对比

### 模式 1: 纯 DALL-E (当前实现)
```
推文 → Claude 分析 → DALL-E 生成 → 发布
```
**优点**: 完全定制，高度相关  
**缺点**: 有成本 ($0.04/张)

### 模式 2: 混合模式
```
推文 → 先找本地/Unsplash → 找不到再 DALL-E
```
**优点**: 平衡成本和质量  
**缺点**: 图片相关性可能不如纯生成

### 模式 3: 条件生成
```
推文 → 判断是否需要图片 → 需要才生成
```
**优点**: 最省成本  
**缺点**: 需要额外判断逻辑

---

## 🔧 高级定制

### 自定义视觉风格
编辑 `src/ai/image_prompt_optimizer.py`：

```python
def build_dalle_prompt(self, visual_elements: Dict[str, Any]) -> str:
    # 添加你的品牌风格
    brand_style = "minimalist, tech startup aesthetic"
    
    prompt = f"""
    {visual_elements['main_subject']}
    Style: {brand_style}  # 强制使用品牌风格
    ...
    """
```

### 支持其他图片生成 API

#### Stable Diffusion
```python
# 已预留接口
prompt = optimizer.build_stable_diffusion_prompt(visual_elements)
# 调用你的 Stable Diffusion API
```

#### Midjourney
```python
# 已预留接口
prompt = optimizer.build_midjourney_prompt(visual_elements)
# 复制 prompt 到 Midjourney Discord Bot
```

---

## 📊 图片质量优化建议

### 1. 提高推文质量
推文写得越具体，生成的图片越精准：
- ❌ "AI 很厉害"
- ✅ "GPT-4 在医学诊断中展现了超越人类医生的准确率"

### 2. 调整视觉元素提取 Prompt
如果图片不够理想，可以微调 `image_prompt_optimizer.py` 中的分析 prompt。

### 3. 使用 HD 质量
```yaml
dalle:
  quality: "hd"  # 成本翻倍但质量更好
```

---

## 🐛 故障排查

### DALL-E 调用失败
```bash
# 检查 API Key
echo $OPENAI_API_KEY

# 检查余额
# 访问 https://platform.openai.com/usage
```

### 图片不相关
- 检查推文是否足够具体
- 查看日志中的 "视觉元素" 是否准确
- 手动调整 `visual_elements`

### 生成速度慢
- DALL-E 3 生成需要 10-30 秒
- 建议异步处理或提前生成

---

## 🎓 示例效果

### 输入推文
```
"比特币突破 10 万美元！加密货币的春天来了吗？"
```

### Claude 分析结果
```json
{
  "main_subject": "金色比特币硬币向上飞升",
  "scene": "深蓝色数字背景，数据流动",
  "style": "现代金融科技风格",
  "mood": "振奋、突破",
  "colors": ["金色", "深蓝"],
  "elements": ["K线图", "上升箭头", "光芒"]
}
```

### 生成的图片
→ 一张金色比特币在数字背景中向上飞升的专业配图

---

想让我添加哪些功能？
1. 支持本地 Stable Diffusion
2. 图片质量评分（生成多张选最佳）
3. 图片风格模板（科技/商务/生活等）
4. 批量生成预览
