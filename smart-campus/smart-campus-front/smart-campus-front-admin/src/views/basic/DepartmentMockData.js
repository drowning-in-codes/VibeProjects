// 生成模拟数据的辅助函数
const generateMockData = () => {
  const departments = [
    // 基础计算机类 (1-20)
    { prefix: '计算机科学与技术', code: 'CS' },
    { prefix: '软件工程', code: 'SE' },
    { prefix: '信息管理', code: 'IM' },
    { prefix: '人工智能', code: 'AI' },
    { prefix: '数据科学', code: 'DS' },
    { prefix: '网络工程', code: 'NE' },
    { prefix: '物联网工程', code: 'IOT' },
    { prefix: '电子商务', code: 'EC' },
    { prefix: '信息安全', code: 'IS' },
    { prefix: '大数据', code: 'BD' },
    { prefix: '云计算', code: 'CC' },
    { prefix: '区块链', code: 'BC' },
    { prefix: '网络安全', code: 'NS' },
    { prefix: '虚拟现实', code: 'VR' },
    { prefix: '增强现实', code: 'AR' },
    { prefix: '游戏开发', code: 'GD' },
    { prefix: '移动应用开发', code: 'MA' },
    { prefix: '前端开发', code: 'FE' },
    { prefix: '后端开发', code: 'BE' },
    { prefix: '全栈开发', code: 'FS' },

    // AI与机器学习类 (21-40)
    { prefix: '机器学习', code: 'ML' },
    { prefix: '深度学习', code: 'DL' },
    { prefix: '计算机视觉', code: 'CV' },
    { prefix: '自然语言处理', code: 'NLP' },
    { prefix: '智能机器人', code: 'IR' },
    { prefix: '语音识别', code: 'SR' },
    { prefix: '图像处理', code: 'IP' },
    { prefix: '模式识别', code: 'PR' },
    { prefix: '智能控制', code: 'IC' },
    { prefix: '专家系统', code: 'ES' },
    { prefix: '知识图谱', code: 'KG' },
    { prefix: '推荐系统', code: 'RS' },
    { prefix: '强化学习', code: 'RL' },
    { prefix: '迁移学习', code: 'TL' },
    { prefix: '联邦学习', code: 'FL' },
    { prefix: '神经网络', code: 'NN' },
    { prefix: '生成对抗网络', code: 'GAN' },
    { prefix: '自动驾驶', code: 'AD' },
    { prefix: '智能制造', code: 'SM' },
    { prefix: '智慧医疗', code: 'SH' },

    // 系统与工程类 (41-60)
    { prefix: '嵌入式系统', code: 'EMS' },
    { prefix: '边缘计算', code: 'EGC' },
    { prefix: '量子计算', code: 'QC' },
    { prefix: '分布式系统', code: 'DIST' },
    { prefix: '微服务架构', code: 'MSA' },
    { prefix: '容器技术', code: 'CT' },
    { prefix: 'DevOps工程', code: 'DO' },
    { prefix: '系统架构', code: 'SA' },
    { prefix: '高性能计算', code: 'HPC' },
    { prefix: '并行计算', code: 'PC' }
  ]

  const leaders = [
    '张教授', '李教授', '王教授', '赵教授', '刘教授', '陈教授', '杨教授', '周教授',
    '吴教授', '郑教授', '冯教授', '何教授', '孙教授', '钱教授', '朱教授', '许教授',
    '袁教授', '韩教授', '秦教授', '尤教授', '卫教授', '蒋教授', '沈教授', '韩教授',
    '杨教授', '朱教授', '秦教授', '尤教授', '许教授', '何教授', '吕教授', '施教授',
    '张院士', '李院士', '王院士', '陈研究员', '林教授', '黄教授', '梁教授', '马教授'
  ]

  const data = []

  for (let i = 0; i < 200; i++) {
    const deptIndex = i % departments.length
    const dept = departments[deptIndex]
    const cycle = Math.floor(i / departments.length)
    const suffix = cycle > 0 ? `(${cycle + 1})` : ''

    // 生成随机日期
    const month = String(Math.floor(Math.random() * 12) + 1).padStart(2, '0')
    const day = String(Math.floor(Math.random() * 28) + 1).padStart(2, '0')
    const hour = String(Math.floor(Math.random() * 14) + 8).padStart(2, '0')
    const minute = String(Math.floor(Math.random() * 60)).padStart(2, '0')

    data.push({
      departmentId: i + 1,
      departmentName: `${dept.prefix}${suffix}学院`,
      departmentCode: `${dept.code}${String(i + 1).padStart(3, '0')}`,
      leader: leaders[Math.floor(Math.random() * leaders.length)],
      contactPhone: `010-${10000000 + Math.floor(Math.random() * 90000000)}`,
      status: Math.random() > 0.15 ? 1 : 0,
      createTime: `2024-${month}-${day} ${hour}:${minute}:00`,
      remark: `负责${dept.prefix}专业的教学与科研工作`
    })
  }

  return data
}

export const mockData = generateMockData()
