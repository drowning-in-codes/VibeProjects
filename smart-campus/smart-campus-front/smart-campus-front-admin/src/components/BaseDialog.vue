<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  // 是否显示弹窗
  visible: {
    type: Boolean,
    default: false
  },
  // 弹窗标题
  title: {
    type: String,
    default: '提示'
  },
  // 弹窗宽度（支持百分比或具体值，如 '50%' 或 '800px'）
  width: {
    type: String,
    default: '50%'
  },
  // 距离顶部的距离
  top: {
    type: String,
    default: '30px'
  },
  // 内容区域 padding
  bodyPadding: {
    type: String,
    default: '20px'
  },
  // 是否显示取消按钮
  showCancel: {
    type: Boolean,
    default: true
  },
  // 是否显示右上角关闭按钮
  showClose: {
    type: Boolean,
    default: true
  },
  // 取消按钮文字
  cancelText: {
    type: String,
    default: '取消'
  },
  // 确认按钮文字
  confirmText: {
    type: String,
    default: '确定'
  },
  // 确认按钮类型
  confirmType: {
    type: String,
    default: 'primary'
  },
  // 是否显示底部按钮区域
  showFooter: {
    type: Boolean,
    default: true
  },
  // 点击遮罩层是否可以关闭
  closeOnClickModal: {
    type: Boolean,
    default: false
  },
  // 是否在关闭时销毁子元素
  destroyOnClose: {
    type: Boolean,
    default: false
  },
  // 自定义按钮列表（高级用法）
  customButtons: {
    type: Array,
    default: () => []
    // 格式: [{ text: '按钮文字', type: 'primary', handler: () => {} }]
  }
})

const emit = defineEmits(['update:visible', 'confirm', 'cancel', 'close'])

const dialogVisible = ref(props.visible)

// 监听外部 visible 变化
watch(
  () => props.visible,
  (val) => {
    dialogVisible.value = val
  }
)

// 监听内部 dialogVisible 变化
watch(dialogVisible, (val) => {
  emit('update:visible', val)
  if (!val) {
    emit('close')
  }
})

// 计算内容区域的最大高度
const contentMaxHeight = computed(() => {
  // 获取视口高度
  const viewportHeight = window.innerHeight
  // 解析 top 值（去掉 px）
  const topValue = parseInt(props.top) || 30
  // 标题区域高度（大约 60px）
  const headerHeight = 60
  // 底部按钮区域高度（大约 70px，包含 padding）
  const footerHeight = props.showFooter ? 70 : 0
  // 计算可用高度
  const availableHeight = viewportHeight - topValue * 2 - headerHeight - footerHeight
  // 返回最大高度
  return `${Math.max(availableHeight, 200)}px`
})

// 计算内容区域样式
const contentStyle = computed(() => {
  return {
    padding: props.bodyPadding,
    maxHeight: contentMaxHeight.value,
    overflowY: 'auto'
  }
})

// 取消
const handleCancel = () => {
  emit('cancel')
  dialogVisible.value = false
}

// 确认
const handleConfirm = () => {
  emit('confirm')
}

// 关闭
const handleClose = () => {
  emit('close')
  dialogVisible.value = false
}
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="title"
    :width="width"
    :top="top"
    :show-close="showClose"
    :close-on-click-modal="closeOnClickModal"
    :destroy-on-close="destroyOnClose"
    @close="handleClose"
  >
    <!-- 内容区域 -->
    <div class="dialog-content" :style="contentStyle">
      <slot></slot>
    </div>

    <!-- 底部按钮区域 -->
    <template v-if="showFooter" #footer>
      <div class="dialog-footer">
        <!-- 自定义按钮（高级用法） -->
        <template v-if="customButtons.length > 0">
          <el-button
            v-for="(btn, index) in customButtons"
            :key="index"
            :type="btn.type || 'default'"
            :link="btn.link || false"
            @click="btn.handler"
          >
            {{ btn.text }}
          </el-button>
        </template>

        <!-- 默认按钮 -->
        <template v-else>
          <el-button v-if="showCancel" link @click="handleCancel">
            {{ cancelText }}
          </el-button>
          <el-button :type="confirmType" @click="handleConfirm">
            {{ confirmText }}
          </el-button>
        </template>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped lang="scss">
.dialog-content {
  // 自定义滚动条样式
  &::-webkit-scrollbar {
    width: 6px;
    height: 6px;
  }

  &::-webkit-scrollbar-thumb {
    background-color: #dcdfe6;
    border-radius: 3px;

    &:hover {
      background-color: #c0c4cc;
    }
  }

  &::-webkit-scrollbar-track {
    background-color: #f5f7fa;
    border-radius: 3px;
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 12px;
}

// 调整 el-dialog 的样式
:deep(.el-dialog) {
  border-radius: 8px;
  overflow: hidden;

  .el-dialog__header {
    padding: 20px 20px 15px;
    border-bottom: 1px solid #ebeef5;
    margin: 0;

    .el-dialog__title {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
    }
  }

  .el-dialog__body {
    padding: 0;
  }

  .el-dialog__footer {
    padding: 15px 20px;
    border-top: 1px solid #ebeef5;
  }
}
</style>
