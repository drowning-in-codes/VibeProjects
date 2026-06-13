# BaseDialog 弹窗组件文档

## 组件简介

基于 Element Plus `el-dialog` 封装的通用弹窗组件，提供灵活的配置选项和标准化的使用方式。

## 功能特性

✅ 自定义标题  
✅ 灵活的宽度设置（百分比或具体值）  
✅ 可配置的距离顶部高度  
✅ 自动计算内容区域最大高度  
✅ 内容超出自动滚动  
✅ 可自定义内容区域 padding  
✅ 灵活的按钮配置  
✅ 取消按钮可选（link 样式）  
✅ 右上角关闭按钮可选  
✅ 自定义按钮列表（高级用法）  
✅ 美观的滚动条样式  

---

## Props 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `visible` | Boolean | `false` | 是否显示弹窗（支持 v-model） |
| `title` | String | `'提示'` | 弹窗标题 |
| `width` | String | `'50%'` | 弹窗宽度（如 '50%'、'800px'） |
| `top` | String | `'30px'` | 距离顶部的距离 |
| `bodyPadding` | String | `'20px'` | 内容区域 padding |
| `showCancel` | Boolean | `true` | 是否显示取消按钮 |
| `showClose` | Boolean | `true` | 是否显示右上角关闭按钮 |
| `cancelText` | String | `'取消'` | 取消按钮文字 |
| `confirmText` | String | `'确定'` | 确认按钮文字 |
| `confirmType` | String | `'primary'` | 确认按钮类型 |
| `showFooter` | Boolean | `true` | 是否显示底部按钮区域 |
| `closeOnClickModal` | Boolean | `false` | 点击遮罩层是否可以关闭 |
| `destroyOnClose` | Boolean | `false` | 关闭时是否销毁子元素 |
| `customButtons` | Array | `[]` | 自定义按钮列表（高级用法） |

---

## Events 事件

| 事件名 | 参数 | 说明 |
|--------|------|------|
| `update:visible` | `(visible: boolean)` | 弹窗显示状态改变时触发 |
| `confirm` | - | 点击确认按钮时触发 |
| `cancel` | - | 点击取消按钮时触发 |
| `close` | - | 弹窗关闭时触发 |

---

## Slots 插槽

| 插槽名 | 说明 |
|--------|------|
| `default` | 弹窗内容区域 |

---

## 基础用法

### 1. 简单示例

```vue
<template>
  <el-button @click="dialogVisible = true">打开弹窗</el-button>

  <BaseDialog
    v-model:visible="dialogVisible"
    title="提示"
    @confirm="handleConfirm"
  >
    <p>这是弹窗内容</p>
  </BaseDialog>
</template>

<script setup>
import { ref } from 'vue'
import BaseDialog from '@/components/BaseDialog.vue'

const dialogVisible = ref(false)

const handleConfirm = () => {
  console.log('确认')
  dialogVisible.value = false
}
</script>
```

---

### 2. 自定义宽度和距离顶部

```vue
<BaseDialog
  v-model:visible="dialogVisible"
  title="大弹窗"
  width="80%"
  top="50px"
>
  <p>宽度 80%，距离顶部 50px</p>
</BaseDialog>

<BaseDialog
  v-model:visible="dialogVisible"
  title="固定宽度弹窗"
  width="600px"
  top="10vh"
>
  <p>宽度 600px，距离顶部 10vh</p>
</BaseDialog>
```

---

### 3. 自定义按钮文字和类型

```vue
<BaseDialog
  v-model:visible="dialogVisible"
  title="删除确认"
  confirm-text="删除"
  confirm-type="danger"
  cancel-text="我再想想"
  @confirm="handleDelete"
>
  <p>确定要删除这条数据吗？</p>
</BaseDialog>
```

---

### 4. 隐藏取消按钮

```vue
<BaseDialog
  v-model:visible="dialogVisible"
  title="只读信息"
  :show-cancel="false"
  confirm-text="知道了"
>
  <p>这是一条通知信息</p>
</BaseDialog>
```

---

### 5. 隐藏右上角关闭按钮

```vue
<BaseDialog
  v-model:visible="dialogVisible"
  title="强制确认"
  :show-close="false"
  :close-on-click-modal="false"
>
  <p>必须点击按钮才能关闭</p>
</BaseDialog>
```

---

### 6. 自定义内容区域 padding

```vue
<!-- 无 padding -->
<BaseDialog
  v-model:visible="dialogVisible"
  title="无内边距"
  body-padding="0"
>
  <div style="padding: 20px; background: #f5f7fa;">
    自定义内容样式
  </div>
</BaseDialog>

<!-- 大 padding -->
<BaseDialog
  v-model:visible="dialogVisible"
  title="大内边距"
  body-padding="40px"
>
  <p>内容区域有 40px 内边距</p>
</BaseDialog>
```

---

### 7. 隐藏底部按钮区域

```vue
<BaseDialog
  v-model:visible="dialogVisible"
  title="纯展示弹窗"
  :show-footer="false"
>
  <p>没有底部按钮</p>
</BaseDialog>
```

---

### 8. 自定义按钮列表（高级用法）

```vue
<BaseDialog
  v-model:visible="dialogVisible"
  title="多按钮操作"
  :custom-buttons="buttons"
>
  <p>自定义多个操作按钮</p>
</BaseDialog>

<script setup>
const buttons = [
  {
    text: '取消',
    link: true,
    handler: () => {
      dialogVisible.value = false
    }
  },
  {
    text: '保存草稿',
    type: 'default',
    handler: () => {
      console.log('保存草稿')
    }
  },
  {
    text: '提交',
    type: 'primary',
    handler: () => {
      console.log('提交')
      dialogVisible.value = false
    }
  }
]
</script>
```

---

### 9. 表单弹窗示例

```vue
<template>
  <BaseDialog
    v-model:visible="dialogVisible"
    title="编辑用户"
    width="600px"
    @confirm="handleSubmit"
    @cancel="handleCancel"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
      <el-form-item label="用户名" prop="username">
        <el-input v-model="form.username" placeholder="请输入用户名" />
      </el-form-item>

      <el-form-item label="邮箱" prop="email">
        <el-input v-model="form.email" placeholder="请输入邮箱" />
      </el-form-item>

      <el-form-item label="角色" prop="role">
        <el-select v-model="form.role" placeholder="请选择角色">
          <el-option label="管理员" value="admin" />
          <el-option label="普通用户" value="user" />
        </el-select>
      </el-form-item>
    </el-form>
  </BaseDialog>
</template>

<script setup>
import { ref, reactive } from 'vue'
import BaseDialog from '@/components/BaseDialog.vue'

const dialogVisible = ref(false)
const formRef = ref(null)

const form = reactive({
  username: '',
  email: '',
  role: ''
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

const handleSubmit = () => {
  formRef.value.validate((valid) => {
    if (valid) {
      console.log('提交表单', form)
      dialogVisible.value = false
    }
  })
}

const handleCancel = () => {
  formRef.value.resetFields()
}
</script>
```

---

### 10. 长内容自动滚动

```vue
<BaseDialog
  v-model:visible="dialogVisible"
  title="长内容弹窗"
  width="700px"
>
  <div v-for="i in 50" :key="i">
    <p>这是第 {{ i }} 段内容</p>
  </div>
</BaseDialog>
```

**说明**：当内容高度超过计算的最大高度时，内容区域会自动出现滚动条。

---

## 内容最大高度计算逻辑

```javascript
// 可用高度 = 视口高度 - 顶部距离*2 - 标题高度 - 底部按钮高度
const availableHeight = window.innerHeight - top*2 - 60 - (showFooter ? 70 : 0)
```

- **视口高度**：`window.innerHeight`
- **顶部距离**：`top` 参数（默认 30px）
- **标题高度**：约 60px（包含 padding 和边框）
- **底部按钮高度**：约 70px（包含 padding 和边框）
- **最小高度**：200px

---

## 样式特点

### 1. 美观的滚动条
- 滚动条宽度：6px
- 滚动条颜色：#dcdfe6
- 悬停颜色：#c0c4cc
- 轨道颜色：#f5f7fa
- 圆角设计

### 2. 弹窗样式
- 圆角：8px
- 标题字号：16px，加粗
- 标题与内容之间有分隔线
- 底部按钮区域有分隔线
- 按钮右对齐，间距 12px

---

## 完整示例：院系表单弹窗

```vue
<template>
  <BaseDialog
    :visible="visible"
    :title="title"
    width="600px"
    :show-cancel="!isView"
    :confirm-text="isView ? '关闭' : '确定'"
    @update:visible="$emit('update:visible', $event)"
    @confirm="handleConfirm"
    @cancel="handleCancel"
    @close="handleClose"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="100px" :disabled="isView">
      <el-form-item label="院系名称" prop="departmentName">
        <el-input v-model="form.departmentName" placeholder="请输入院系名称" />
      </el-form-item>

      <el-form-item label="院系代码" prop="departmentCode">
        <el-input v-model="form.departmentCode" placeholder="请输入院系代码" />
      </el-form-item>

      <el-form-item label="负责人" prop="leader">
        <el-input v-model="form.leader" placeholder="请输入负责人姓名" />
      </el-form-item>

      <el-form-item label="状态" prop="status">
        <el-radio-group v-model="form.status">
          <el-radio :value="1">启用</el-radio>
          <el-radio :value="0">禁用</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
  </BaseDialog>
</template>
```

---

## 最佳实践

### 1. 使用 v-model:visible
```vue
<!-- 推荐 -->
<BaseDialog v-model:visible="dialogVisible" />

<!-- 不推荐 -->
<BaseDialog 
  :visible="dialogVisible" 
  @update:visible="dialogVisible = $event" 
/>
```

### 2. 表单验证后再关闭
```javascript
const handleConfirm = () => {
  formRef.value.validate((valid) => {
    if (valid) {
      // 验证通过才关闭
      emit('confirm', form)
      dialogVisible.value = false
    }
  })
}
```

### 3. 关闭时重置表单
```javascript
const handleClose = () => {
  formRef.value?.resetFields()
}
```

### 4. 查看模式的处理
```vue
<BaseDialog
  :show-cancel="!isView"
  :confirm-text="isView ? '关闭' : '确定'"
>
  <el-form :disabled="isView">
    <!-- 表单内容 -->
  </el-form>
</BaseDialog>
```

---

## 常见问题

### Q1: 内容区域没有滚动条？
A: 确保内容高度超过了计算的最大高度。可以通过浏览器开发者工具查看 `max-height` 是否生效。

### Q2: 如何让弹窗居中显示？
A: 调整 `top` 参数。如果想完全居中，可以设置 `top="15vh"`。

### Q3: 如何禁用 ESC 键关闭？
A: Element Plus 的 `el-dialog` 默认支持 ESC 键关闭，如需禁用需要自定义处理。

### Q4: 如何添加加载状态？
A: 在确认按钮上添加 loading 状态需要使用自定义按钮列表功能。

---

## 浏览器兼容性

✅ Chrome 90+  
✅ Firefox 88+  
✅ Safari 14+  
✅ Edge 90+  

---

## 更新日期

2026-06-07
