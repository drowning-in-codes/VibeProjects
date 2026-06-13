<script setup>
import { ref, reactive } from 'vue'
import BaseDataTable from '@/components/BaseDataTable.vue'
import DepartmentForm from './DepartmentForm.vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { mockData } from './DepartmentMockData'

// 搜索表单
const searchForm = reactive({
  departmentName: '',
  status: ''
})

// 表格数据
const tableData = ref({
  totalCount: 0,
  pageSize: 15,
  pageNo: 1,
  pageTotal: 1,
  list: []
})

const loading = ref(false)

// 表格列配置
const columns = [
  { prop: 'departmentId', label: '院系ID', width: '120', align: 'center' },
  { prop: 'departmentName', label: '院系名称', minWidth: '150' },
  { prop: 'departmentCode', label: '院系代码', width: '150', align: 'center' },
  { prop: 'leader', label: '负责人', width: '120', align: 'center' },
  { prop: 'contactPhone', label: '联系电话', width: '140', align: 'center' },
  { prop: 'status', label: '状态', width: '100', align: 'center', slot: 'status' },
  { prop: 'createTime', label: '创建时间', width: '180', align: 'center' },
  { prop: 'action', label: '操作', width: '220', align: 'center', fixed: 'right', slot: 'action' }
]

// 弹窗控制
const dialogVisible = ref(false)
const dialogTitle = ref('')
const formData = ref(null)

// 选中的行
const selectedRows = ref([])

// 搜索
const handleSearch = () => {
  tableData.value.pageNo = 1
  loadData()
}

// 重置搜索
const handleReset = () => {
  searchForm.departmentName = ''
  searchForm.status = ''
  tableData.value.pageNo = 1
  loadData()
}

// 加载数据
const loadData = () => {
  loading.value = true

  // 模拟异步请求
  setTimeout(() => {
    let filteredData = [...mockData]

    // 按名称筛选
    if (searchForm.departmentName) {
      filteredData = filteredData.filter(item =>
        item.departmentName.includes(searchForm.departmentName)
      )
    }

    // 按状态筛选
    if (searchForm.status !== '') {
      filteredData = filteredData.filter(item => item.status === Number(searchForm.status))
    }

    // 分页
    const totalCount = filteredData.length
    const start = (tableData.value.pageNo - 1) * tableData.value.pageSize
    const end = start + tableData.value.pageSize
    const list = filteredData.slice(start, end)

    tableData.value = {
      totalCount,
      pageSize: tableData.value.pageSize,
      pageNo: tableData.value.pageNo,
      pageTotal: Math.ceil(totalCount / tableData.value.pageSize),
      list
    }

    loading.value = false
  }, 300)
}

// 新增
const handleAdd = () => {
  dialogTitle.value = '新增院系'
  formData.value = null
  dialogVisible.value = true
}

// 编辑
const handleEdit = (row) => {
  dialogTitle.value = '编辑院系'
  formData.value = { ...row }
  dialogVisible.value = true
}

// 查看
const handleView = (row) => {
  dialogTitle.value = '查看院系'
  formData.value = { ...row }
  dialogVisible.value = true
}

// 删除
const handleDelete = (row) => {
  ElMessageBox.confirm(`确定要删除院系"${row.departmentName}"吗？`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  })
    .then(() => {
      // 模拟删除操作
      ElMessage.success('删除成功')
      loadData()
    })
    .catch(() => {
      // 取消删除
    })
}

// 批量删除
const handleBatchDelete = () => {
  if (selectedRows.value.length === 0) {
    ElMessage.warning('请先选择要删除的数据')
    return
  }

  const names = selectedRows.value.map(row => row.departmentName).join('、')
  ElMessageBox.confirm(`确定要删除以下院系吗？\n${names}`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  })
    .then(() => {
      ElMessage.success(`成功删除 ${selectedRows.value.length} 条数据`)
      selectedRows.value = []
      loadData()
    })
    .catch(() => {
      // 取消删除
    })
}

// 弹窗确认
const handleDialogConfirm = (data) => {
  console.log('保存数据：', data)
  ElMessage.success(dialogTitle.value.includes('新增') ? '新增成功' : '保存成功')
  dialogVisible.value = false
  loadData()
}

// 分页改变
const handlePageChange = (page) => {
  tableData.value.pageNo = page
  loadData()
}

const handleSizeChange = (size) => {
  tableData.value.pageSize = size
  tableData.value.pageNo = 1
  loadData()
}

// 选择变化
const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

// 初始化加载数据
loadData()
</script>

<template>
  <div class="department-container">
    <div class="page-title">院系管理</div>

    <!-- 搜索区域 -->
    <el-card class="search-card" shadow="never">
      <el-form :model="searchForm" inline>
        <el-form-item label="院系名称">
          <el-input
            v-model="searchForm.departmentName"
            placeholder="请输入院系名称"
            clearable
            style="width: 200px"
            @keyup.enter="handleSearch"
          />
        </el-form-item>

        <el-form-item label="状态">
          <el-select
            v-model="searchForm.status"
            placeholder="请选择状态"
            clearable
            style="width: 150px"
            @change="handleSearch"
          >
            <el-option label="启用" :value="1" />
            <el-option label="禁用" :value="0" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>
            <span>搜索</span>
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>
            <span>重置</span>
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 表格区域 -->
    <el-card class="table-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">院系列表</span>
          <div class="header-actions">
            <el-button type="danger" plain @click="handleBatchDelete">
              <el-icon><Delete /></el-icon>
              <span>批量删除</span>
            </el-button>
            <el-button type="primary" @click="handleAdd">
              <el-icon><Plus /></el-icon>
              <span>新增院系</span>
            </el-button>
          </div>
        </div>
      </template>

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
        <!-- 状态列 -->
        <template #status="{ row }">
          <el-tag :type="row.status === 1 ? 'success' : 'danger'">
            {{ row.status === 1 ? '启用' : '禁用' }}
          </el-tag>
        </template>

        <!-- 操作列 -->
        <template #action="{ row }">
          <el-button type="primary" link @click="handleView(row)">
            <el-icon><View /></el-icon>
            查看
          </el-button>
          <el-button type="primary" link @click="handleEdit(row)">
            <el-icon><Edit /></el-icon>
            编辑
          </el-button>
          <el-button type="danger" link @click="handleDelete(row)">
            <el-icon><Delete /></el-icon>
            删除
          </el-button>
        </template>
      </BaseDataTable>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <DepartmentForm
      v-model:visible="dialogVisible"
      :title="dialogTitle"
      :form-data="formData"
      @confirm="handleDialogConfirm"
    />
  </div>
</template>

<style scoped lang="scss">
.department-container {
  .page-title {
    font-size: 20px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 20px;
  }

  .search-card {
    margin-bottom: 16px;

    :deep(.el-card__body) {
      padding: 18px 20px;
    }

    .el-form {
      margin-bottom: 0;
    }

    .el-form-item {
      margin-bottom: 0;
    }
  }

  .table-card {
    .card-header {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .card-title {
        font-size: 16px;
        font-weight: 600;
        color: #303133;
      }

      .header-actions {
        display: flex;
        gap: 12px;
      }
    }
  }
}
</style>
