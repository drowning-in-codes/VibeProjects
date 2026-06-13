// 菜单配置文件
export const menuConfig = [
  {
    id: '1',
    name: '首页',
    code: 'home',
    children: [
      {
        id: '1-1',
        name: '数据看板',
        code: 'home-dashboard',
        path: '/dashboard'
      }
    ]
  },
  {
    id: '2',
    name: '基础数据',
    code: 'basic',
    children: [
      {
        id: '2-1',
        name: '院系管理',
        code: 'basic-department',
        path: '/department'
      },
      {
        id: '2-2',
        name: '专业管理',
        code: 'basic-major',
        path: '/major'
      },
      {
        id: '2-3',
        name: '班级管理',
        code: 'basic-class',
        path: '/class'
      },
      {
        id: '2-4',
        name: '学生管理',
        code: 'basic-student',
        path: '/student'
      },
      {
        id: '2-5',
        name: '教师管理',
        code: 'basic-teacher',
        path: '/teacher'
      }
    ]
  },
  {
    id: '3',
    name: '资源中心',
    code: 'resource',
    children: [
      {
        id: '3-1',
        name: '资源管理',
        code: 'resource-manage',
        path: '/resource'
      }
    ]
  },
  {
    id: '4',
    name: '教学业务',
    code: 'teaching',
    children: [
      {
        id: '4-1',
        name: '课程管理',
        code: 'teaching-course',
        path: '/course'
      },
      {
        id: '4-2',
        name: '习题管理',
        code: 'teaching-exercise',
        path: '/exercise'
      },
      {
        id: '4-3',
        name: '试卷管理',
        code: 'teaching-paper',
        path: '/paper'
      },
      {
        id: '4-4',
        name: '考试管理',
        code: 'teaching-exam',
        path: '/exam'
      }
    ]
  },
  {
    id: '5',
    name: '系统管理',
    code: 'system',
    children: [
      {
        id: '5-1',
        name: '公告管理',
        code: 'system-notice',
        path: '/notice'
      },
      {
        id: '5-2',
        name: '权限管理',
        code: 'system-permission',
        path: '/permission'
      }
    ]
  }
]
