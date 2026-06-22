# 图片生成配置速查表

## 🚀 快速配置

### 场景 1: 预算有限（推荐入门）

```yaml
# config.yaml
image:
  enabled: true
  provider: "dalle"
  
  dalle:
    model: "dall-e-2"
    size: "512x512"
```

**月成本**: ~$2 (每天 4 条)  
**适合**: 个人测试、学习使用

---

### 场景 2: 标准质量

```yaml
image:
  enabled: true
  provider: "dalle"
  
  dalle:
    model: "dall-e-3"
    size: "1024x1024"
    quality: "standard"
```

**月成本**: ~$5-8 (每天 4 条)  
**适合**: 品牌账号、专业运营

---

### 场景 3: 顶级质量

```yaml
image:
  enabled: true
  provider: "dalle"
  
  dalle:
    model: "dall-e-3"
    size: "1024x1024"
    quality: "hd"
```

**月成本**: ~$10-15 (每天 4 条)  
**适合**: 高端品牌、商业用途

---

### 场景 4: 极致省钱

```yaml
image:
  enabled: true
  provider: "dalle"
  fallback_to_unsplash: true     # Unsplash 优先
  
  dalle:
    model: "dall-e-2"
    size: "256x256"                # 最小尺寸
```

**月成本**: < $1 (Unsplash 免费，DALL-E 备用)  
**适合**: 高频发布、预算极低

---

## 📊 一键对比

| 配置 | 模型 | 尺寸 | 质量 | 单价 | 月成本(120张) |
|-----|------|------|------|------|-------------|
| 极省 | DALL-E 2 | 256x256 | ⭐⭐ | $0.016 | $1.92 |
| 入门 | DALL-E 2 | 512x512 | ⭐⭐⭐ | $0.018 | $2.16 |
| 推荐 | DALL-E 2 | 1024x1024 | ⭐⭐⭐ | $0.020 | $2.40 |
| 标准 | DALL-E 3 | 1024x1024 | ⭐⭐⭐⭐ | $0.040 | $4.80 |
| 高级 | DALL-E 3 HD | 1024x1024 | ⭐⭐⭐⭐⭐ | $0.080 | $9.60 |

---

## 🎯 选择建议

```
我该用哪个？
  │
  ├─ 只是测试？ → DALL-E 2 (512x512)
  │
  ├─ 个人账号？ → DALL-E 2 (1024x1024)
  │
  ├─ 品牌运营？ → DALL-E 3 Standard
  │
  └─ 商业用途？ → DALL-E 3 HD
```

---

## ⚡ 切换方法

### 从 DALL-E 3 降级到 DALL-E 2

```bash
# 编辑 config.yaml
nano config.yaml

# 修改这两行
dalle:
  model: "dall-e-2"       # 改为 dall-e-2
  size: "512x512"         # 改为 512x512

# 重启
python main.py start
```

### 从 DALL-E 2 升级到 DALL-E 3

```bash
dalle:
  model: "dall-e-3"       # 改为 dall-e-3
  size: "1024x1024"       # 保持 1024x1024
  quality: "standard"     # 添加这行
```

---

## 💡 实用技巧

### 1. 先小后大
```yaml
# 第 1 周：测试用 DALL-E 2
dalle:
  model: "dall-e-2"

# 第 2 周：验证效果后升级
dalle:
  model: "dall-e-3"
```

### 2. 分时段使用
```python
# 白天高峰 → DALL-E 2
# 晚上重要推文 → DALL-E 3
```

### 3. 混合策略
```yaml
# 80% 用 Unsplash（免费）
# 20% 用 DALL-E 2（备用）
fallback_to_unsplash: true
```

---

## 📝 配置文件位置

```bash
# 主配置文件
./config.yaml

# 环境变量
./.env

# 重启生效
python main.py start
```

---

查看完整对比：[DALLE_COMPARISON.md](DALLE_COMPARISON.md)
