<script setup>
import { ref, reactive, watch } from 'vue'
import BaseDialog from '@/components/BaseDialog.vue'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  title: {
    type: String,
    default: '院系信息'
  },
  formData: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['update:visible', 'confirm'])

const isView = ref(false)

const form = reactive({
  departmentId: null,
  departmentName: '',
  departmentCode: '',
  leader: '',
  contactPhone: '',
  status: 1,
  remark: ''
})

const rules = {
  departmentName: [{ required: true, message: '请输入院系名称', trigger: 'blur' }],
  departmentCode: [{ required: true, message: '请输入院系代码', trigger: 'blur' }],
  leader: [{ required: true, message: '请输入负责人', trigger: 'blur' }],
  contactPhone: [
    { required: true, message: '请输入联系电话', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$|^0\d{2,3}-?\d{7,8}$/, message: '请输入正确的联系电话', trigger: 'blur' }
  ]
}

const formRef = ref(null)

// 监听 visible 变化
watch(
  () => props.visible,
  (val) => {
    if (val) {
      isView.value = props.title.includes('查看')
      if (props.formData) {
        Object.assign(form, props.formData)
      } else {
        resetForm()
      }
    }
  }
)

// 重置表单
const resetForm = () => {
  form.departmentId = null
  form.departmentName = ''
  form.departmentCode = ''
  form.leader = ''
  form.contactPhone = ''
  form.status = 1
  form.remark = ''
  formRef.value?.clearValidate()
}

// 确认
const handleConfirm = () => {
  if (isView.value) {
    emit('update:visible', false)
    return
  }

  formRef.value.validate((valid) => {
    if (valid) {
      emit('confirm', { ...form })
      emit('update:visible', false)
    }
  })
}

// 取消
const handleCancel = () => {
  emit('update:visible', false)
}

// 关闭时重置表单
const handleClose = () => {
  resetForm()
}
</script>

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
        <el-input v-model="form.departmentName" placeholder="请输入院系名称" maxlength="50" />
      </el-form-item>

      <el-form-item label="院系代码" prop="departmentCode">
        <el-input v-model="form.departmentCode" placeholder="请输入院系代码" maxlength="20" />
      </el-form-item>

      <el-form-item label="负责人" prop="leader">
        <el-input v-model="form.leader" placeholder="请输入负责人姓名" maxlength="20" />
      </el-form-item>

      <el-form-item label="联系电话" prop="contactPhone">
        <el-input v-model="form.contactPhone" placeholder="请输入联系电话" maxlength="20" />
      </el-form-item>

      <el-form-item label="状态" prop="status">
        <el-radio-group v-model="form.status">
          <el-radio :value="1">启用</el-radio>
          <el-radio :value="0">禁用</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="备注" prop="remark">
        <el-input
          v-model="form.remark"
          type="textarea"
          :rows="3"
          placeholder="请输入备注信息"
          maxlength="200"
          show-word-limit
        />
      </el-form-item>
    </el-form>
  </BaseDialog>
</template>

<style scoped lang="scss">
// 无需额外样式，BaseDialog 已处理
</style>
