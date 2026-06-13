# BaseDataTable 组件优化说明

## 已完成的优化

### 1. ✅ Element Plus 中文语言配置

**问题**：分页组件显示英文文本（如 "item/page" 等）

**解决方案**：
- 在 `src/main.js` 中引入中文语言包
- 配置 Element Plus 使用中文语言

```javascript
import zhCn from 'element-plus/es/locale/lang/zh-cn'

app.use(ElementPlus, {
  locale: zhCn
})
```

**效果**：
- 分页器显示中文："条/页"、"共 X 条"、"跳至"
- 表格空数据显示中文："暂无数据"
- 所有 Element Plus 组件统一使用中文

---

### 2. ✅ 封装表格默认无边框

**问题**：表格默认显示边框，无法自定义

**解决方案**：
- 新增 `border` 属性，默认值为 `false`
- 调用方可按需启用边框

```vue
<!-- 无边框（默认） -->
<BaseDataTable :columns="columns" :data="tableData" />

<!-- 带边框 -->
<BaseDataTable :columns="columns" :data="tableData" :border="true" />
```

**效果**：
- 默认表格更简洁
- 按需显示边框，灵活性更高

---

### 3. ✅ 表格动态计算高度，撑满可见区域

**问题**：
- 表格高度固定或计算不准确
- 无法充分利用可见区域
- 外部页面出现滚动条

**解决方案**：
1. **容器引用**：使用 `ref="containerRef"` 获取容器元素
2. **动态计算**：基于容器实际高度减去分页器高度
3. **响应式监听**：
   - 监听窗口大小变化 (`window.resize`)
   - 监听容器大小变化 (`ResizeObserver`)
   - 监听数据变化 (`watch`)
4. **生命周期管理**：
   - `onMounted` 时初始化计算
   - `onUnmounted` 时清理监听器

```javascript
// 计算表格高度
const calculateTableHeight = () => {
  if (props.height) return // 如果外部指定了高度，使用外部高度

  setTimeout(() => {
    if (containerRef.value) {
      const containerHeight = containerRef.value.offsetHeight
      const paginationHeight = total.value > 0 ? 70 : 0
      const availableHeight = containerHeight - paginationHeight
      tableHeight.value = Math.max(availableHeight, 200)
    }
  }, 100)
}

// 监听窗口大小变化
window.addEventListener('resize', calculateTableHeight)

// 使用 ResizeObserver 监听容器大小变化
resizeObserver = new ResizeObserver(() => {
  calculateTableHeight()
})
resizeObserver.observe(containerRef.value)
```

**效果**：
- ✅ 表格自动撑满父容器可用高度
- ✅ 表格内部滚动，页面无滚动条
- ✅ 窗口大小改变时自动调整
- ✅ 数据变化时自动重新计算
- ✅ 最小高度 200px，避免过小

---

## 使用示例

### 完整示例（院系管理）

```vue
<template>
  <div class="department-container">
    <div class="page-title">院系管理</div>
    
    <!-- 搜索区域 -->
    <el-card class="search-card">
      <!-- 搜索表单 -->
    </el-card>

    <!-- 表格区域 -->
    <el-card class="table-card">
      <BaseDataTable
        :columns="columns"
        :data="tableData"
        :loading="loading"
        :show-selection="true"
        :show-index="true"
        :border="true"
        @page-change="handlePageChange"
        @size-change="handleSizeChange"
        @selection-change="handleSelectionChange"
      >
        <!-- 自定义插槽 -->
        <template #status="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'danger'">
            {{ row.status === 1 ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </BaseDataTable>
    </el-card>
  </div>
</template>

<style scoped lang="scss">
.department-container {
  height: 100%; // 重要：容器需要有明确高度
  display: flex;
  flex-direction: column;
  
  .table-card {
    flex: 1; // 重要：让表格卡片占据剩余空间
    display: flex;
    flex-direction: column;
    overflow: hidden; // 重要：防止溢出
    
    :deep(.el-card__body) {
      flex: 1;
      overflow: hidden; // 重要：让表格内部滚动
      display: flex;
      flex-direction: column;
    }
  }
}
</style>
```

---

## 关键要点

### 1. 父容器样式要求

为了让表格正确计算高度，父容器必须：
- 有明确的高度（`height: 100%` 或具体数值）
- 使用 `display: flex` 布局
- 表格卡片使用 `flex: 1` 占据剩余空间
- 设置 `overflow: hidden` 防止溢出

### 2. BaseDataTable Props

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `columns` | Array | 必填 | 列配置 |
| `data` | Object | `{}` | 数据源（包含 list、totalCount 等） |
| `loading` | Boolean | `false` | 加载状态 |
| `showSelection` | Boolean | `false` | 是否显示复选框 |
| `showIndex` | Boolean | `false` | 是否显示序号列 |
| `border` | Boolean | `false` | 是否显示边框 |
| `height` | String/Number | `null` | 固定高度（不传则自动计算） |
| `pageSizes` | Array | `[10, 15, 20, 50, 100]` | 每页条数选项 |

### 3. 事件

| 事件 | 参数 | 说明 |
|------|------|------|
| `page-change` | `page` | 页码改变 |
| `size-change` | `size` | 每页条数改变 |
| `selection-change` | `selection` | 选择项改变 |

### 4. 暴露方法

```javascript
// 获取组件实例
const tableRef = ref(null)

// 调用方法
tableRef.value.clearSelection() // 清空选择
tableRef.value.toggleRowSelection(row, true) // 切换行选中
tableRef.value.toggleAllSelection() // 切换全选
```

---

## 最佳实践

1. **页面布局**：使用 flex 布局，确保容器有明确高度
2. **表格高度**：不传 `height` 属性，让组件自动计算
3. **边框显示**：根据设计需求决定是否启用 `border`
4. **分页配置**：根据数据量选择合适的 `pageSizes`
5. **性能优化**：大数据量时启用虚拟滚动（Element Plus Pro）

---

## 浏览器兼容性

- ✅ Chrome 64+
- ✅ Firefox 69+
- ✅ Safari 13.1+
- ✅ Edge 79+

（ResizeObserver 支持范围）

---

## 更新日期

2026-06-07
