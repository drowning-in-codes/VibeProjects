import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('adminToken') || '')
  const userInfo = ref(null)
  const menuList = ref([])
  const menuCodeList = ref([])

  // 设置 token
  const setToken = (newToken) => {
    token.value = newToken
    if (newToken) {
      localStorage.setItem('adminToken', newToken)
    } else {
      localStorage.removeItem('adminToken')
    }
  }

  // 设置用户信息
  const setUserInfo = (info) => {
    userInfo.value = info
  }

  // 设置菜单列表
  const setMenuList = (list) => {
    menuList.value = list
    // 提取所有菜单编码
    const codes = []
    list.forEach(menu => {
      codes.push(menu.code)
      if (menu.children) {
        menu.children.forEach(child => {
          codes.push(child.code)
        })
      }
    })
    menuCodeList.value = codes
  }

  // 检查是否拥有某个菜单权限
  const hasMenuCode = (code) => {
    return menuCodeList.value.includes(code)
  }

  // 清除登录态
  const clearLoginState = () => {
    token.value = ''
    userInfo.value = null
    menuList.value = []
    menuCodeList.value = []
    localStorage.removeItem('adminToken')
  }

  return {
    token,
    userInfo,
    menuList,
    menuCodeList,
    setToken,
    setUserInfo,
    setMenuList,
    hasMenuCode,
    clearLoginState
  }
})
