<script setup>
import { ref } from 'vue'

const pageTitle = ref('公告管理')
</script>

<template>
  <div class="page-container">
    <div class="page-title">{{ pageTitle }}</div>
    <div class="page-content">
      <p>公告管理功能开发中...</p>
    </div>
  </div>
</template>

<style scoped lang="scss">
.page-container {
  .page-title {
    font-size: 20px;
    font-weight: 600;
    color: #303133;
    margin-bottom: 20px;
  }

  .page-content {
    color: #606266;
  }
}
</style>
