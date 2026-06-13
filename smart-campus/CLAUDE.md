# Smart Campus 项目规则

高校在线学习平台，前后端分离，后端拆成两个独立服务（管理端 + 用户端），各自带独立拦截器与登录态。

# 项目结构

后端 `smart-campus-java/`（Maven 多模块）：

- `smart-campus-common`：公共模块，包路径 `com.smart.campus`。承载 PO / DTO / VO / Query、Service / Mapper、Redis 组件、异常、枚举、工具类。
- `smart-campus-admin`：管理端服务，包路径 `com.smart.admin`。承载 Controller、Biz（业务编排）、管理端专用 DTO/VO。独立启动，运行在管理端端口。
- `smart-campus-web`：用户端服务，包路径 `com.smart.web`。承载 Controller、Biz、用户端专用 DTO/VO。独立启动，运行在用户端端口。

依赖方向：`admin → common`、`web → common`。common 不允许反向依赖任何端。

前端 `smart-campus-front/`：

- `smart-campus-front-admin`：管理后台前端工程。
- `smart-campus-front-web`：学生端前端工程。

> 包名提醒：common 用 `com.smart.campus`，admin 用 `com.smart.admin`，web 用 `com.smart.web`。新增类必须落到正确的包路径，不要混。

# 系统角色

- 系统管理员：管理基础数据 + 资源 + 教学业务。
- 教师：维护资源 + 自己名下课程的教学业务。
- 学生：学习课程 + 在线考试 + 学习分析。

角色字段约定在 `UserInfo.roleType`。

# 接口与路径

- 全局上下文：`/api`，由 `server.servlet.context-path` 提供，路径中**不再重复**写 `admin` / `web`。
- 路径形式：`/api/<模块名>/<动作>`，模块名小驼峰；常用动作：`loadDataList`、`add`、`update`、`delete`、`detail`、`getXxxOptions`（下拉用）。
- 管理接口归 admin 模块、用户接口归 web 模块；两端互不复用 Controller。

# 鉴权与权限

- 管理端 token 走 header `adminToken`，由管理端登录拦截器校验，并配合 Redis 登录组件做有效期管理。
- 用户端 token 走 header `studentToken`，由用户端登录拦截器校验。
- 管理端接口必须打权限注解，权限编码与系统菜单表中的编码一一对应；权限不通过则抛业务异常。
- 当前登录用户统一从登录上下文持有器（ThreadLocal）取，禁止在 Controller / Service 里再次手动解析 token。

# 核心业务域

- 基础数据：院系、专业、班级、用户（含教师与学生）。
- 教学业务：课程 → 章节 → 课时 → 课时资源；选课通过班级与课程的关联表。
- 习题与试卷：题库、题目选项、试卷、试卷题目关联。
- 考试：考试信息、考试与班级关联。
- 作业评估：作业提交、提交题目。
- 学习数据：课程进度（课程级）、课时进度（含视频时间点）、学习日志。
- 资源：资源信息（视频/文档），上传走分片 + Redis 队列异步处理。
- 系统：菜单、角色菜单、系统通知、站内消息。

# 业务规则

- 课程：归属一名教师；教师只能维护自己的课程；学生通过班级选课。
- 章节：两级结构（章节 → 课时），课时下挂资源。
- 考试：客观题自动评分，主观题人工评分。
- 学习记录：服务端记录学习时长、视频时间点；前端按课时恢复播放进度。

# 字段与返回约定

- 后端统一返回 `ResponseVO<T>`，不直接返回 Entity / PO。
- 分页参数继承统一基类，分页结果使用统一的分页结果 VO；前后端分页字段保持一致。
- 数据库字段下划线、Java 字段驼峰，由 MyBatis 配置自动映射；**前端字段保持与后端驼峰一致**，禁止前端起别名。
- 时间字段统一格式化为 `yyyy-MM-dd HH:mm:ss`（GMT+8），禁止返回时间戳。
- 主键：业务实体多为 String UUID（如课程 ID / 章节 ID / 课时 ID / 资源 ID），基础数据多为自增整数。

# 禁止行为

- 禁止前后端字段不一致或私自重命名 PO 字段。
- 禁止生成 mock 数据，联调以真实接口为准。
- 禁止管理端接口不带权限注解。
- 禁止用户端接口暴露管理端字段（创建人、排序权重、审核状态等）。
- 禁止把仅一端使用的类放进 common 模块。
- 禁止 Controller / Biz / Service / Mapper 越层（Controller 不能直接调 Mapper，Mapper 不能反查 Service 等）。

# 子规则索引

- 后端通用：`smart-campus-java/CLAUDE.md`
- 前端通用：`smart-campus-front/CLAUDE.md`
- 各子模块 / 前端工程根目录下的 `AGENTS.md` 为补充约束。