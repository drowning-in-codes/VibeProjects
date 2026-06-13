import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import router from '@/router'

// 创建 axios 实例
const request = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    const userStore = useUserStore()
    if (userStore.token) {
      config.headers.adminToken = userStore.token
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response) => {
    const res = response.data

    // 登录失效
    if (res.code === 401 || res.code === 403) {
      const userStore = useUserStore()
      userStore.clearLoginState()
      router.push({
        path: '/login',
        query: { redirect: router.currentRoute.value.fullPath }
      })
      ElMessage.error(res.message || '登录已失效，请重新登录')
      return Promise.reject(new Error(res.message || '登录已失效'))
    }

    // 业务错误
    if (res.code !== 200) {
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message || '请求失败'))
    }

    // 成功返回业务数据
    return res.data
  },
  (error) => {
    ElMessage.error(error.message || '网络请求失败')
    return Promise.reject(error)
  }
)

export default request
