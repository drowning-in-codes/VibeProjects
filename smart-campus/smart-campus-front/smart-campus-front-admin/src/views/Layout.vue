<script setup>
import { ref, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { menuConfig } from '@/router/menu'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()

// 当前选中的一级菜单
const activeFirstMenu = ref('1')

// 模拟用户信息
const userInfo = computed(() => {
  return userStore.userInfo || { username: '管理员' }
})

// 当前二级菜单列表
const secondMenuList = computed(() => {
  const firstMenu = menuConfig.find((menu) => menu.id === activeFirstMenu.value)
  return firstMenu ? firstMenu.children : []
})

// 当前一级菜单名称
const firstMenuName = computed(() => {
  const firstMenu = menuConfig.find((menu) => menu.id === activeFirstMenu.value)
  return firstMenu ? firstMenu.name : ''
})

// 当前选中的二级菜单路径
const activeSecondMenu = computed(() => route.path)

// 切换一级菜单
const handleFirstMenuClick = (menuId) => {
  activeFirstMenu.value = menuId
  // 自动跳转到第一个二级菜单
  const firstMenu = menuConfig.find((menu) => menu.id === menuId)
  if (firstMenu && firstMenu.children && firstMenu.children.length > 0) {
    router.push(firstMenu.children[0].path)
  }
}

// 切换二级菜单
const handleSecondMenuClick = (path) => {
  router.push(path)
}

// 退出登录
const handleLogout = () => {
  userStore.clearLoginState()
  router.push('/login')
}

// 初始化：根据当前路由设置选中的一级菜单
const initActiveMenu = () => {
  const currentPath = route.path
  for (const firstMenu of menuConfig) {
    if (firstMenu.children) {
      for (const secondMenu of firstMenu.children) {
        if (secondMenu.path === currentPath) {
          activeFirstMenu.value = firstMenu.id
          return
        }
      }
    }
  }
}

initActiveMenu()
</script>

<template>
  <div class="layout-container">
    <!-- 顶部区域 -->
    <div class="layout-header">
      <!-- Logo 和项目名称 -->
      <div class="header-left">
        <div class="logo">
          <svg viewBox="0 0 1024 1024" width="24" height="24">
            <path
              d="M512 128L128 384l384 256 384-256L512 128z m0 576L235 519.3 128 590.7 512 846.9l384-256.2-107-71.4L512 704z"
              fill="#409eff"
            />
          </svg>
        </div>
        <div class="project-name">智慧校园后台</div>
      </div>

      <!-- 一级菜单 -->
      <div class="header-center">
        <div
          v-for="menu in menuConfig"
          :key="menu.id"
          :class="['first-menu-item', { active: activeFirstMenu === menu.id }]"
          @click="handleFirstMenuClick(menu.id)"
        >
          {{ menu.name }}
        </div>
      </div>

      <!-- 用户信息 -->
      <div class="header-right">
        <el-dropdown @command="handleLogout">
          <div class="user-info">
            <el-icon><Avatar /></el-icon>
            <span class="username">{{ userInfo.username }}</span>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="logout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 内容区域 -->
    <div class="layout-main">
      <!-- 左侧二级菜单 -->
      <div class="layout-sidebar">
        <el-card class="sidebar-card">
          <div class="sidebar-title">{{ firstMenuName }}</div>
          <div class="second-menu-list">
            <div
              v-for="menu in secondMenuList"
              :key="menu.id"
              :class="['second-menu-item', { active: activeSecondMenu === menu.path }]"
              @click="handleSecondMenuClick(menu.path)"
            >
              {{ menu.name }}
            </div>
          </div>
        </el-card>
      </div>

      <!-- 右侧内容区 -->
      <div class="layout-content">
        <el-card class="content-card">
          <router-view />
        </el-card>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.layout-container {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #f0f2f5;
}

// 顶部区域
.layout-header {
  height: 60px;
  background: #ffffff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.08);
  border-bottom: 1px solid #e8f0fe;

  .header-left {
    display: flex;
    align-items: center;
    gap: 12px;

    .logo {
      width: 36px;
      height: 36px;
      background: #ecf5ff;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .project-name {
      font-size: 20px;
      font-weight: 600;
      color: #1e3a5f;
      letter-spacing: 1px;
    }
  }

  .header-center {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    height: 100%;

    .first-menu-item {
      font-size: 15px;
      color: #606266;
      cursor: pointer;
      padding: 0 20px;
      height: 100%;
      display: flex;
      align-items: center;
      position: relative;
      transition: all 0.3s;

      &:hover {
        color: #409eff;
      }

      &.active {
        color: #409eff;
        font-weight: 500;

        &::after {
          content: '';
          position: absolute;
          bottom: 0;
          left: 20px;
          right: 20px;
          height: 3px;
          background: #409eff;
          border-radius: 2px 2px 0 0;
        }
      }
    }
  }

  .header-right {
    .user-info {
      display: flex;
      align-items: center;
      gap: 8px;
      color: #606266;
      cursor: pointer;
      padding: 6px 12px;
      border-radius: 6px;
      transition: all 0.3s;

      &:hover {
        background: #ecf5ff;
        color: #409eff;
      }

      .username {
        font-size: 14px;
      }
    }
  }
}

// 主体区域
.layout-main {
  flex: 1;
  display: flex;
  gap: 16px;
  padding: 16px;
  overflow: hidden;
}

// 左侧菜单
.layout-sidebar {
  width: 200px;
  flex-shrink: 0;

  .sidebar-card {
    height: 100%;
    border-radius: 8px;

    :deep(.el-card__body) {
      height: 100%;
      padding: 0;
      display: flex;
      flex-direction: column;
    }

    .sidebar-title {
      font-size: 16px;
      font-weight: 600;
      color: #303133;
      padding: 16px;
      border-bottom: 1px solid #ebeef5;
    }

    .second-menu-list {
      flex: 1;
      overflow-y: auto;
      padding: 8px;

      .second-menu-item {
        padding: 12px 16px;
        margin-bottom: 4px;
        font-size: 14px;
        color: #606266;
        cursor: pointer;
        border-radius: 6px;
        transition: all 0.3s;

        &:hover {
          background: #f5f7fa;
          color: #409eff;
        }

        &.active {
          background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
          color: white;
          font-weight: 500;
          box-shadow: 0 2px 6px rgba(64, 158, 255, 0.35);
        }
      }
    }
  }
}

// 右侧内容区
.layout-content {
  flex: 1;
  overflow: hidden;

  .content-card {
    height: 100%;
    border-radius: 8px;

    :deep(.el-card__body) {
      height: 100%;
      padding: 20px;
      overflow: visible;
    }
  }
}
</style>

