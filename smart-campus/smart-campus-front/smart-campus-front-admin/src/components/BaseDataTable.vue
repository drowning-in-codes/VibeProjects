<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  // 列配置
  columns: {
    type: Array,
    required: true,
    // 格式: [{ label: '姓名', prop: 'name', width: '120', slot: 'name', align: 'center' }]
  },
  // 数据源
  data: {
    type: Object,
    default: () => ({
      totalCount: 0,
      pageSize: 15,
      pageNo: 1,
      pageTotal: 1,
      list: []
    })
  },
  // 是否显示加载状态
  loading: {
    type: Boolean,
    default: false
  },
  // 是否显示复选框
  showSelection: {
    type: Boolean,
    default: false
  },
  // 是否显示序号列
  showIndex: {
    type: Boolean,
    default: false
  },
  // 是否显示边框
  border: {
    type: Boolean,
    default: false
  },
  // 表格高度（不传则自动计算）
  height: {
    type: [String, Number],
    default: null
  },
  // 每页显示条数选项
  pageSizes: {
    type: Array,
    default: () => [10, 15, 20, 50, 100]
  }
})

const emit = defineEmits(['page-change', 'size-change', 'selection-change'])

const tableRef = ref(null)
const tableHeight = ref(null)
const containerRef = ref(null)

// 计算表格数据
const tableData = computed(() => props.data.list || [])
const total = computed(() => props.data.totalCount || 0)
const currentPage = computed(() => props.data.pageNo || 1)
const pageSize = computed(() => props.data.pageSize || 15)

// 计算表格高度
const computedHeight = computed(() => {
  if (props.height) {
    return props.height
  }
  return tableHeight.value
})

// 监听数据变化，自动计算高度
watch(
  () => tableData.value,
  () => {
    calculateTableHeight()
  },
  { flush: 'post' }
)

// 监听窗口大小变化
watch(
  () => props.data,
  () => {
    calculateTableHeight()
  },
  { deep: true, flush: 'post' }
)

// 计算表格高度（自动适应内容）
const calculateTableHeight = () => {
  if (props.height) return

  // 延迟计算，等待DOM渲染
  setTimeout(() => {
    if (containerRef.value) {
      // 获取可视区域高度
      const viewportHeight = window.innerHeight
      // 获取容器距离顶部的距离
      const containerRect = containerRef.value.getBoundingClientRect()
      const containerTop = containerRect.top
      // 预留底部空间（分页器高度 + 卡片底部padding + 页面底部边距）
      const bottomSpace = total.value > 0 ? 100 : 50
      // 计算可用高度
      const availableHeight = viewportHeight - containerTop - bottomSpace
      // 设置最小高度和最大高度
      tableHeight.value = Math.max(Math.min(availableHeight, 800), 300)
    }
  }, 100)
}

// 页码变化
const handleCurrentChange = (page) => {
  emit('page-change', page)
}

// 每页条数变化
const handleSizeChange = (size) => {
  emit('size-change', size)
}

// 复选框选择变化
const handleSelectionChange = (selection) => {
  emit('selection-change', selection)
}

// 清空选择
const clearSelection = () => {
  tableRef.value?.clearSelection()
}

// 切换行选中状态
const toggleRowSelection = (row, selected) => {
  tableRef.value?.toggleRowSelection(row, selected)
}

// 切换所有行选中状态
const toggleAllSelection = () => {
  tableRef.value?.toggleAllSelection()
}

// 暴露方法给父组件
defineExpose({
  clearSelection,
  toggleRowSelection,
  toggleAllSelection,
  tableRef
})

// 组件挂载后计算高度
let resizeObserver = null

onMounted(() => {
  calculateTableHeight()

  // 监听窗口大小变化
  window.addEventListener('resize', calculateTableHeight)

  // 使用 ResizeObserver 监听容器大小变化
  if (containerRef.value) {
    resizeObserver = new ResizeObserver(() => {
      calculateTableHeight()
    })
    resizeObserver.observe(containerRef.value)
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', calculateTableHeight)
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
})
</script>

<template>
  <div ref="containerRef" class="base-data-table">
    <el-table
      ref="tableRef"
      :data="tableData"
      :height="computedHeight"
      v-loading="loading"
      :border="border"
      stripe
      style="width: 100%"
      :header-cell-style="{
        background: '#f5f7fa',
        color: '#606266',
        fontWeight: '600',
        fontSize: '14px'
      }"
      @selection-change="handleSelectionChange"
    >
      <!-- 复选框列 -->
      <el-table-column
        v-if="showSelection"
        type="selection"
        width="55"
        align="center"
        fixed="left"
      />

      <!-- 序号列 -->
      <el-table-column
        v-if="showIndex"
        type="index"
        label="序号"
        width="60"
        align="center"
        fixed="left"
        :index="(index) => (currentPage - 1) * pageSize + index + 1"
      />

      <!-- 动态列 -->
      <el-table-column
        v-for="column in columns"
        :key="column.prop"
        :prop="column.prop"
        :label="column.label"
        :width="column.width"
        :min-width="column.minWidth"
        :align="column.align || 'left'"
        :fixed="column.fixed"
        :sortable="column.sortable"
        :show-overflow-tooltip="column.showOverflowTooltip !== false"
      >
        <!-- 自定义列内容 -->
        <template v-if="column.slot" #default="scope">
          <slot
            :name="column.slot"
            :row="scope.row"
            :index="scope.$index"
            :column="column"
          ></slot>
        </template>

        <!-- 默认渲染 -->
        <template v-if="!column.slot && column.formatter" #default="scope">
          {{ column.formatter(scope.row, column) }}
        </template>
      </el-table-column>

      <!-- 空数据提示 -->
      <template #empty>
        <el-empty description="暂无数据" :image-size="100" />
      </template>
    </el-table>

    <!-- 分页器 -->
    <div v-if="total > 0" class="pagination-container">
      <el-pagination
        :current-page="currentPage"
        :page-size="pageSize"
        :page-sizes="pageSizes"
        :total="total"
        background
        layout="total, sizes, prev, pager, next, jumper"
        @current-change="handleCurrentChange"
        @size-change="handleSizeChange"
      />
    </div>
  </div>
</template>

<style scoped lang="scss">
.base-data-table {
  width: 100%;

  :deep(.el-table) {
    font-size: 14px;

    .el-table__cell {
      padding: 12px 0;
    }

    // 表头样式
    .el-table__header-wrapper {
      .el-table__cell {
        background: #f5f7fa;
      }
    }

    // 空数据样式
    .el-table__empty-block {
      min-height: 200px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }

  .pagination-container {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    margin-top: 16px;
    padding: 12px 0;

    :deep(.el-pagination) {
      .el-pagination__total {
        margin-right: 10px;
        color: #606266;
      }

      .btn-prev,
      .btn-next,
      .el-pager li {
        background-color: #fff;
        border: 1px solid #dcdfe6;
      }

      .btn-prev:disabled,
      .btn-next:disabled {
        background-color: #f5f7fa;
      }

      .el-pager li.is-active {
        background-color: #409eff;
        color: #fff;
        border-color: #409eff;
      }
    }
  }
}
</style>
