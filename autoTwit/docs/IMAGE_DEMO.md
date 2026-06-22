# 图片生成功能演示

## 🎯 核心原理

**推文驱动的智能配图生成**

```
推文文本 → Claude 分析视觉元素 → DALL-E 生成配图 → 发布
```

---

## 📸 实际案例演示

### 案例 1: 科技类推文

#### 输入推文
```
GPT-4 的多模态能力展现了 AI 的飞跃，从文本到图像理解，
我们离真正的通用人工智能还有多远？
```

#### Claude 分析结果
```json
{
  "main_subject": "未来感的人工智能大脑芯片",
  "scene": "深邃的科技空间，蓝紫色光线流动",
  "style": "科幻数字艺术，现代极简",
  "mood": "神秘、前瞻、启发思考",
  "colors": ["深蓝", "紫色", "青色"],
  "elements": ["神经网络连接", "数据流", "光效"],
  "avoid": ["文字", "具体人脸", "公司 logo"]
}
```

#### DALL-E Prompt
```
A high-quality digital illustration for social media:

Main subject: 未来感的人工智能大脑芯片
Scene: 深邃的科技空间，蓝紫色光线流动
Style: 科幻数字艺术，现代极简
Mood: 神秘、前瞻、启发思考
Color palette: 深蓝 and 紫色
Additional elements: 神经网络连接, 数据流, 光效

Requirements:
- Professional and polished
- Suitable for Twitter/X post
- No text or words in the image
- 16:9 or square aspect ratio
- Avoid: 文字, 具体人脸, 公司 logo
```

#### 生成效果
→ 一张蓝紫色调的 AI 大脑芯片，神经网络般的光线流动，科技感十足

---

### 案例 2: 商业类推文

#### 输入推文
```
创业的本质不是追逐风口，而是解决真实问题。
当你的产品让用户说"这正是我需要的"，成功就不远了。
```

#### Claude 分析结果
```json
{
  "main_subject": "向上攀登的登山者剪影",
  "scene": "日出时分的山峰顶端",
  "style": "温暖鼓舞人心的写实风格",
  "mood": "坚定、希望、成就感",
  "colors": ["金色", "橙色", "深蓝"],
  "elements": ["山峰轮廓", "晨光", "向上的路径"],
  "avoid": ["文字", "品牌标志", "过于商业化"]
}
```

#### 生成效果
→ 温暖的日出背景，登山者站在山顶，象征创业者的征途

---

### 案例 3: 生活感悟类推文

#### 输入推文
```
咖啡凉了可以重新煮，但错过的时光不会重来。
珍惜当下，做你想做的事。
```

#### Claude 分析结果
```json
{
  "main_subject": "一杯冒着热气的咖啡",
  "scene": "温暖的窗边，阳光透过窗帘",
  "style": "温馨生活摄影风格，景深效果",
  "mood": "平静、温暖、治愈",
  "colors": ["暖棕色", "米白", "金色光线"],
  "elements": ["木桌", "柔和光线", "植物"],
  "avoid": ["文字", "人物", "过于商业"]
}
```

#### 生成效果
→ 一杯咖啡在窗边，温暖的自然光，生活感十足

---

## 🎨 视觉风格对比

### 推文风格 → 图片风格映射

| 推文类型 | 视觉风格 | 色调 | 情绪 |
|---------|---------|------|------|
| 科技/AI | 科幻数字艺术 | 蓝紫色 | 神秘前瞻 |
| 商业/创业 | 现代简洁 | 商务蓝/橙 | 专业坚定 |
| 生活感悟 | 温馨摄影 | 暖色调 | 治愈平静 |
| 金融/投资 | 专业图表风格 | 金色/绿色 | 严肃专业 |
| 健身/运动 | 活力动感 | 鲜艳对比 | 积极向上 |

---

## 🔧 使用方法

### 方法 1: 命令行测试
```bash
# 生成推文并预览配图
python main.py generate "人工智能的未来"

# 输出:
# ==================================================
# GPT-4 展现了惊人的推理能力...
# ==================================================
# 📷 配图路径: ./temp/dalle_123456.png
```

### 方法 2: 自动发布
```bash
# 启动定时系统，自动生成带图推文
python main.py start

# 日志:
# [INFO] 正在分析推文内容，提取视觉元素...
# [INFO] 使用 DALL-E 生成图片...
# [INFO] 推文发布成功（带图片）
```

### 方法 3: 自定义推文 + 配图
```bash
# 先生成不带图的推文
python main.py generate --no-image

# 手动修改推文后，生成配图
python -c "
from src.ai.image import ImageManager
img_mgr = ImageManager()
path = await img_mgr.get_image_for_tweet('你的推文内容')
print(path)
"

# 发布
python main.py post "你的推文内容" ./temp/image.png
```

---

## 💡 进阶技巧

### 1. 强制特定视觉风格
编辑 `src/ai/image_prompt_optimizer.py`:
```python
def build_dalle_prompt(self, visual_elements):
    # 添加你的品牌风格
    BRAND_STYLE = "minimalist tech startup aesthetic, pastel colors"
    
    prompt = f"""
    {visual_elements['main_subject']}
    Brand style: {BRAND_STYLE}  # 强制品牌风格
    ...
    """
```

### 2. 针对不同推文类型使用不同模板
```python
# 在 ImagePromptOptimizer 中添加
def get_style_template(self, tweet_content: str) -> str:
    if "AI" in tweet_content or "技术" in tweet_content:
        return "sci-fi futuristic digital art"
    elif "创业" in tweet_content or "商业" in tweet_content:
        return "modern professional business style"
    else:
        return "warm lifestyle photography"
```

### 3. 批量预生成图片
```python
# 提前生成一批图片，减少发布时等待时间
topics = ["AI", "创业", "投资", "健康"]
for topic in topics:
    content, image = await generator.generate_tweet(topic=topic)
    # 保存到本地图库
```

---

## 📊 质量优化建议

### ✅ 好的推文（易生成高质量图片）
```
❌ "今天天气真好"
✅ "清晨的阳光透过落地窗，一杯热咖啡和一本好书，这就是完美的周末"

❌ "AI 很厉害"
✅ "GPT-4 在医学影像诊断中达到了 95% 的准确率，超越了普通医生的水平"

❌ "区块链有前景"
✅ "比特币突破 10 万美元，去中心化金融正在改写传统金融格局"
```

### 推文撰写技巧
1. **具体场景** - 描述具体的场景和细节
2. **视觉化词汇** - 使用颜色、形状、动作等视觉化词汇
3. **情绪明确** - 表达清晰的情绪（振奋、平静、神秘等）
4. **避免纯抽象** - 抽象概念需要转化为具体意象

---

## 🚀 性能优化

### 生成速度
- **DALL-E 3**: 10-30 秒/张
- **优化方案**: 提前批量生成，或使用本地 Stable Diffusion

### 成本控制
```yaml
# config.yaml
image:
  enabled: true
  provider: "dalle"
  
  # 策略 1: 降低频率（每天 1 次）
  scheduler:
    post_interval_hours: 24
  
  # 策略 2: 使用 standard 质量
  dalle:
    quality: "standard"  # 不用 hd
  
  # 策略 3: 启用 Unsplash 备选
  fallback_to_unsplash: true
```

---

想看更多功能？
- [ ] 图片加水印/品牌 logo
- [ ] 多张图片生成选最佳
- [ ] 视频配图（GIF/短视频）
- [ ] 图片 OCR 检测（确保无文字）
