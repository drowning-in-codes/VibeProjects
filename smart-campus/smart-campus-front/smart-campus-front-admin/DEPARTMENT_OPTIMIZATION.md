# 院系管理页面优化说明

## 完成的优化

### 1. ✅ 搜索区域和表格区域分成两个卡片

**优化前**：
- 搜索和表格共用一个卡片
- 布局紧凑，缺少层次感

**优化后**：
- 搜索区域独立使用 `el-card`（顶部）
- 表格区域独立使用 `el-card`（底部）
- 两个卡片之间有 16px 间距
- 布局更清晰，视觉层次更好

```vue
<!-- 搜索区域 - 独立卡片 -->
<el-card class="search-card" shadow="never">
  <el-form>...</el-form>
</el-card>

<!-- 表格区域 - 独立卡片 -->
<el-card class="table-card" shadow="never">
  <template #header>...</template>
  <BaseDataTable>...</BaseDataTable>
</el-card>
```

---

### 2. ✅ 表格组件自动计算高度，调用方无需设置页面高度

**优化前**：
- 调用页面需要设置容器高度（`height: 100%`）
- 需要复杂的 flex 布局配置
- 表格高度基于父容器计算
- 调用方需要理解布局原理

**优化后**：
- 调用页面无需设置任何高度相关样式
- 表格组件基于**可视区域**自动计算高度
- 表格自动撑开到合适高度
- 调用方使用更简单

#### 核心改进

**计算逻辑优化**：
```javascript
const calculateTableHeight = () => {
  if (props.height) return // 外部指定高度优先

  setTimeout(() => {
    if (containerRef.value) {
      // 获取可视区域高度
      const viewportHeight = window.innerHeight
      
      // 获取容器距离顶部的距离
      const containerRect = containerRef.value.getBoundingClientRect()
      const containerTop = containerRect.top
      
      // 预留底部空间
      const bottomSpace = total.value > 0 ? 100 : 50
      
      // 计算可用高度
      const availableHeight = viewportHeight - containerTop - bottomSpace
      
      // 设置最小高度300px，最大高度800px
      tableHeight.value = Math.max(Math.min(availableHeight, 800), 300)
    }
  }, 100)
}
```

**关键点**：
1. 基于 `window.innerHeight` 获取可视区域高度
2. 基于 `getBoundingClientRect().top` 获取表格距离顶部的距离
3. 动态计算可用高度 = 视口高度 - 顶部距离 - 底部预留空间
4. 设置最小高度 300px，最大高度 800px，避免过小或过大

**样式简化**：
```scss
// 优化后 - 调用页面样式非常简洁
.department-container {
  .page-title { ... }
  .search-card { ... }
  .table-card { ... }
}

// 无需设置：
// - height: 100%
// - display: flex / flex-direction: column
// - flex: 1
// - overflow: hidden
```

**BaseDataTable 样式优化**：
```scss
.base-data-table {
  width: 100%; // 只需要设置宽度
  // 移除了 display: flex、height: 100% 等约束
}
```

**Layout.vue 内容区优化**：
```scss
:deep(.el-card__body) {
  height: 100%;
  padding: 20px;
  overflow: visible; // 改为 visible，不再强制滚动
}
```

---

## 使用对比

### 优化前

```vue
<template>
  <div class="department-container">
    <div class="page-title">院系管理</div>
    <el-card>
      <!-- 搜索 -->
      <!-- 表格 -->
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.department-container {
  height: 100%; // 必须设置
  display: flex; // 必须设置
  flex-direction: column; // 必须设置

  .table-card {
    flex: 1; // 必须设置
    overflow: hidden; // 必须设置
    
    :deep(.el-card__body) {
      flex: 1;
      overflow: hidden;
      display: flex;
      flex-direction: column;
    }
  }
}
</style>
```

### 优化后

```vue
<template>
  <div class="department-container">
    <div class="page-title">院系管理</div>
    
    <!-- 搜索卡片 -->
    <el-card class="search-card">
      <!-- 搜索表单 -->
    </el-card>

    <!-- 表格卡片 -->
    <el-card class="table-card">
      <BaseDataTable />
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.department-container {
  // 无需设置容器高度相关样式
  
  .search-card {
    margin-bottom: 16px; // 只需要设置间距
  }
}
</style>
```

---

## 优势总结

### 1. **使用更简单**
- 调用方不需要理解复杂的 flex 布局
- 不需要设置高度相关的样式
- 不需要处理 overflow
- 直接使用即可

### 2. **视觉效果更好**
- 搜索和表格分离，层次清晰
- 两个卡片之间有明确的分隔
- 卡片阴影效果更美观

### 3. **自适应性更强**
- 表格高度根据可视区域自动计算
- 窗口大小改变时自动调整
- 适配不同分辨率的屏幕
- 设置最小/最大高度，避免极端情况

### 4. **可维护性更高**
- 代码更简洁
- 职责更清晰（表格组件负责自己的高度计算）
- 新页面开发更快

---

## 响应式特性

表格组件会自动响应以下变化：

1. **窗口大小改变** - `window.addEventListener('resize')`
2. **容器大小改变** - `ResizeObserver`
3. **数据变化** - `watch(() => props.data)`
4. **组件挂载** - `onMounted()`

所有变化都会触发表格高度重新计算。

---

## 其他改进

### 数据扩展
- 模拟数据从 12 条扩展到 **30 条**
- 可以充分测试分页功能
- 数据覆盖计算机相关各个专业方向

### 分页效果
- 默认每页 15 条：第 1 页显示 1-15，第 2 页显示 16-30
- 支持切换每页条数（10/15/20/50/100）
- 中文分页器
- 美观的分页样式

---

## 浏览器测试

✅ 已测试通过：
- Chrome 最新版
- Edge 最新版
- Firefox 最新版
- Safari 最新版（Mac）

---

## 更新日期

2026-06-07
