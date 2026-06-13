import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: () => import('@/views/Layout.vue'),
      redirect: '/dashboard',
      children: [
        {
          path: '/dashboard',
          name: 'Dashboard',
          component: () => import('@/views/Dashboard.vue'),
          meta: { requiresAuth: true, menuCode: 'home-dashboard', title: '数据看板' }
        },
        {
          path: '/department',
          name: 'Department',
          component: () => import('@/views/basic/Department.vue'),
          meta: { requiresAuth: true, menuCode: 'basic-department', title: '院系管理' }
        },
        {
          path: '/major',
          name: 'Major',
          component: () => import('@/views/basic/Major.vue'),
          meta: { requiresAuth: true, menuCode: 'basic-major', title: '专业管理' }
        },
        {
          path: '/class',
          name: 'Class',
          component: () => import('@/views/basic/Class.vue'),
          meta: { requiresAuth: true, menuCode: 'basic-class', title: '班级管理' }
        },
        {
          path: '/student',
          name: 'Student',
          component: () => import('@/views/basic/Student.vue'),
          meta: { requiresAuth: true, menuCode: 'basic-student', title: '学生管理' }
        },
        {
          path: '/teacher',
          name: 'Teacher',
          component: () => import('@/views/basic/Teacher.vue'),
          meta: { requiresAuth: true, menuCode: 'basic-teacher', title: '教师管理' }
        },
        {
          path: '/resource',
          name: 'Resource',
          component: () => import('@/views/resource/Resource.vue'),
          meta: { requiresAuth: true, menuCode: 'resource-manage', title: '资源管理' }
        },
        {
          path: '/course',
          name: 'Course',
          component: () => import('@/views/teaching/Course.vue'),
          meta: { requiresAuth: true, menuCode: 'teaching-course', title: '课程管理' }
        },
        {
          path: '/exercise',
          name: 'Exercise',
          component: () => import('@/views/teaching/Exercise.vue'),
          meta: { requiresAuth: true, menuCode: 'teaching-exercise', title: '习题管理' }
        },
        {
          path: '/paper',
          name: 'Paper',
          component: () => import('@/views/teaching/Paper.vue'),
          meta: { requiresAuth: true, menuCode: 'teaching-paper', title: '试卷管理' }
        },
        {
          path: '/exam',
          name: 'Exam',
          component: () => import('@/views/teaching/Exam.vue'),
          meta: { requiresAuth: true, menuCode: 'teaching-exam', title: '考试管理' }
        },
        {
          path: '/notice',
          name: 'Notice',
          component: () => import('@/views/system/Notice.vue'),
          meta: { requiresAuth: true, menuCode: 'system-notice', title: '公告管理' }
        },
        {
          path: '/permission',
          name: 'Permission',
          component: () => import('@/views/system/Permission.vue'),
          meta: { requiresAuth: true, menuCode: 'system-permission', title: '权限管理' }
        }
      ]
    }
  ]
})

// 路由守卫：未登录跳转与菜单权限校验
router.beforeEach((to, from, next) => {
  // 设置页面标题
  if (to.meta.title) {
    document.title = `${to.meta.title} - 智慧校园后台`
  }
  // TODO: 接入登录页后启用未登录跳转与菜单权限校验
  next()
})

export default router
