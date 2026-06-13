定义项目规则和能力
CLAUDE.md：定义规则
Skill：定义能力

CLAUDE.md定义
vibe-coding/
├─ CLAUDE.md
├─ .claude/
│  └─ skills/
│     ├─ java-module
│     ├─ vue-admin-page
│     ├─ vue-web-page
│     ├─ smart-campus-java
│     ├─ smart-campus-front
│
└─ smart-campus/
   ├─ CLAUDE.md
   ├─ smart-campus-java/
   │  └─ CLAUDE.md
   └─ smart-campus-front/
      └─ CLAUDE.md
工作空间 CLAUDE.md
vibe-coding/CLAUDE.md
# Workspace Rules

前后端分离项目工作空间

# 技术规范

后端统一：

- SpringBoot 3.x
- MySQL 8
- Redis

前端统一：

- Vue3
- JavaScript
- Vite
- Element Plus

# 接口规范

- 统一接口风格
- 接口名称必须带模块前缀
- 示例：courseInfo/loadCourseInfoList、courseInfo/getCourseInfo

# 输出要求

- 所有代码必须可直接运行
- 禁止伪代码
- 禁止省略 import/require
- 优先复用现有模块、工具、枚举
- 新增文件必须明确标注完整路径

# 目录规则

- admin：后台管理接口
- web：用户端接口
- common：公共模块
- front-admin：管理后台前端
- front-web：用户端前端

# 开发原则

- 保持与现有代码风格完全一致
- 保持命名规范统一
- 严格分离 PO / DTO / VO
- 统一返回 ResponseVO<T>
ResponseVO<T> 统一返回结构:
{
    "status":"success",
    "code": 200,
    "info": "成功",
    "data": T
}
# 禁止行为

- 禁止修改无关代码
- 禁止随意升级依赖
- 禁止破坏现有接口
- 禁止覆盖我手动修改的代码
项目级  CLAUDE.md
vibe-coding/smart-campus/CLAUDE.md
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
后端 Java CLAUDE.md
vibe-coding/smart-campus/smart-campus-java/CLAUDE.md
# Smart Campus 后端规则（smart-campus-java）

Spring Boot 3 + MyBatis（自定义泛型 Mapper，**不是 MyBatis Plus**）+ MySQL 8 + Redis。

# 模块与包路径

| 模块 | 包路径 | 职责 |
|---|---|---|
| smart-campus-common | `com.smart.campus.*` | PO / DTO / VO / Query、Service / Mapper、Redis 组件、异常、枚举、工具类 |
| smart-campus-admin | `com.smart.admin.*` | 管理端 Controller、Biz、管理端专用 DTO/VO；独立启动 |
| smart-campus-web | `com.smart.web.*` | 用户端 Controller、Biz、用户端专用 DTO/VO；独立启动 |

依赖方向：`admin → common`、`web → common`。common 不允许反向依赖端模块。

启动类位于各端模块根包；扫描范围覆盖 `com.smart`，Mapper 扫描指向 `com.smart.campus.mappers`。

# 分层规范

```
Controller → Biz → Service → Mapper → 数据库
```

- **Controller**（admin / web 模块）：参数接收、参数校验、调用 Biz、返回统一响应。不写业务逻辑。
- **Biz**（admin / web 模块）：业务编排层。承担权限校验、跨 Service 组合、组装返回 VO 等编排职责。命名形如 `XxxAdminBiz` / `XxxWebBiz`。
- **Service / ServiceImpl**（common 模块）：单领域业务逻辑，事务边界落在这一层。Service 接口与实现类分两个包（`service` / `service.impl`）。
- **Mapper**（common 模块）：仅做单表 CRUD 或简单连表。复杂查询写在 XML，XML 放 common 模块的 `resources/mappers/` 下。
- **PO**：与表一对一映射，字段名 / 类型保持与表一致。

# 实体类分工

- **PO**：表映射对象，放 common 的 `entity/po`。Date 字段使用统一的 JSON 格式化注解（`yyyy-MM-dd HH:mm:ss`，时区 GMT+8）。
- **DTO**：接收前端入参，放 common 的 `entity/dto`。需要校验时使用分组校验注解。
- **VO**：返回前端的数据结构，放 common 的 `entity/vo`；若仅服务于某一端的复杂返回结构，可放对应端模块下的 `entity/vo`。
- **Query**：分页查询参数，继承统一分页基类，放 common 的 `entity/query`。模糊匹配字段以 `Fuzzy` 后缀约定（如 `nameFuzzy`）。

主键策略：业务实体多为 String UUID（课程 / 章节 / 课时 / 资源等），基础数据多为自增整数（班级 / 专业 / 院系 / 用户等）。

# Controller 规范

- 类注解：`@RestController`、`@RequestMapping("/<模块名>")`、`@Validated`。管理端再加权限注解（类级提供默认编码，方法级覆盖）。
- 继承公共基础 Controller，使用其提供的成功 / 业务错误返回方法，**不要自己 new 响应对象**。
- 路径中**不要写** `/api/admin/` 或 `/api/web/`：`/api` 由 context-path 提供，`admin` / `web` 由服务隔离。
- 入参：列表查询用 Query 对象（GET 或 POST 均可，按团队规范一致即可），写操作用 DTO 对象 + `@RequestBody`。
- 出参：始终是统一的响应包装类型。

# 鉴权与登录态

- 管理端：登录拦截器读 header `adminToken`，查 Redis 登录组件验证，写入登录上下文持有器（ThreadLocal）。
- 用户端：登录拦截器读 header `studentToken`，逻辑同上。
- 业务代码取当前登录用户**只能**从登录上下文持有器取，禁止再解析 token。
- 权限拒绝：抛业务异常（带权限错误码），由全局异常处理统一转响应。

# 统一返回与异常

- 所有 Controller 返回统一响应包装：包含状态、错误码、提示信息、业务数据四个字段。
- 业务错误码集中维护在响应码枚举里（如成功、系统错误、业务错误、未登录、无权限）。
- 业务异常一律抛自定义业务异常，由全局异常处理转响应。**禁止在 Controller / Service 里 catch 后吞掉错误**。

# 分页

- Query 对象继承统一分页基类，含页码、页大小、排序字段、内部分页对象。
- 查询流程：先 count，再按页大小构造分页对象、塞回 Query，再查列表，最后封装为统一分页结果 VO。
- 默认页大小由公共枚举提供（推荐 15 / 20 等档位）。

# 数据库与字段

- 库名固定，开启下划线到驼峰自动映射。
- 公共字段：创建时间、更新时间；多数表有状态字段（整数枚举：1 正常 / 0 停用）。**无统一的软删除字段**，按需在业务里判断。
- 资源 / 视频相关字段命名稳定（URL、时长、HLS 索引等），前端依赖，禁止改名。
- DDL 与基础数据 SQL 放在后端工程根目录，作为版本化的初始化脚本。

# Redis 使用

- 登录态、学习进度、资源上传 session、资源处理任务队列均有现成的 Redis 组件，**直接复用**，不要新造工具类。
- Service / Biz 通过依赖注入使用这些组件；禁止 Controller 直接操作 RedisTemplate。

# 开发规范

- Controller 只做"收 → 派发 → 回"；业务逻辑在 Biz 或 Service。
- 跨 Service 的组合放 Biz；单表 / 单领域事务边界放 Service。
- Mapper 复杂查询写 XML；禁止用字符串拼接 SQL。
- 公共能力（异常、枚举、常量、工具）下沉到 common；端专用类放对应端模块。

# 禁止行为

- 禁止在 Controller 写 SQL 或操作 RedisTemplate。
- 禁止直接返回 Entity / PO 给前端（应通过响应包装类返回）。
- 禁止在循环里调 Mapper（N+1）。批量场景走批量方法或 IN 查询。
- 禁止吞异常 / 自定义响应结构绕过统一返回。
- 禁止在 common 模块新增仅一端使用的类。
- 禁止管理端 Controller 不带权限注解。
- 禁止在 Controller / Service 自行解析 token，统一走拦截器 + 登录上下文。
- 禁止使用 MyBatis Plus 风格 API（Wrapper / IService 等）。
- 禁止 admin 复用 web 的 Controller，反之亦然。

# 子模块约束

详见各模块下的 `AGENTS.md`，与本文件冲突时以 `AGENTS.md` 中更细化的约束为准。

前端 CLAUDE.md
vibe-coding/smart-campus/smart-campus-front/CLAUDE.md
# Smart Campus 前端规则（smart-campus-front）

Vue 3 + JavaScript（**不使用 TypeScript**）+ Vite + Pinia + Vue Router 4 + Element Plus + Axios + Sass。

两个独立工程：

- `smart-campus-front-admin`：管理后台，服务管理员 / 教师。token header 名 `adminToken`，代理目标为管理端后端服务。
- `smart-campus-front-web`：学生端，服务学生。token header 名 `studentToken`，代理目标为用户端后端服务。

> 两个工程**互不共享代码**。共用约定与组件由各自工程独立维护，不要相互 import。

# 编码规范

- 全部 `<script setup>` + Composition API。
- 接口请求统一封装到 `src/api/<module>.js`，由统一的 axios 实例发出。**禁止在页面 / 组件直接 import axios**。
- 接口路径与后端模块名保持一致，以 `/<模块名>/<动作>` 形式调用（baseURL `/api` 由 axios 实例配置）。

# 目录约定（两端通用）

- `src/api/`：业务模块按文件拆分，并维护统一的请求入口文件。
- `src/views/`：页面，按业务子目录组织。
- `src/components/`：公共组件。管理端的项目级标准组件以 `Base` 前缀命名。
- `src/stores/`：Pinia store，登录态 + 业务 store。
- `src/router/`：路由配置；管理端单独维护菜单配置文件。
- `src/utils/`：请求封装、token 工具、消息 / 确认框工具、业务工具函数。
- `src/assets/`：样式、图标、图片。

# 请求层约定

- axios 实例 baseURL 固定为 `/api`，生产环境可由环境变量拼接外部域名前缀。
- 请求拦截器：从登录态读取 token，写入对应 header（管理端 / 用户端 header 名不同）。
- 响应拦截器：
  - 成功响应直接返回业务数据；
  - 登录失效响应码统一跳转登录页（携带 `redirect`），业务页面**不要重复处理**；
  - 其他业务错误默认弹错，调用方可通过参数关闭错误弹窗（如静默上报场景）。
- 列表返回字段固定为统一结构（总数、页码、页大小、列表数组）；建议在 api 文件中做兜底归一。

# 路由与权限

- 管理端：路由集中维护，与菜单配置文件同步；路由 `meta` 至少包含"是否需要登录""菜单编码"两项。路由守卫统一处理未登录跳转与菜单权限校验。
- 学生端：所有学习页面都需要登录；无角色细分。
- 按钮级权限：管理端通过登录 store 暴露的"是否拥有菜单编码"方法控制按钮显隐。**不**自定义指令。

# 状态管理

- 登录 store 负责：token、用户信息、菜单树、菜单编码列表。
- token 通过工具函数与 localStorage 同步读写；**不引入** pinia 持久化插件。
- 业务 store 按需建，命名以 `useXxxStore` 为模板。

# UI 与样式

- 全局样式入口由各工程自己维护；字体栈与滚动条样式在全局样式里统一。
- Element Plus 走默认主题；如需主题定制集中在样式入口文件，不散落各页面。
- 全部中文界面，禁止生产页面残留英文 placeholder / label。

## 管理后台 UI 约束（强制）

- 页面三段式：**搜索区 → 表格 → 分页**。
- 列表必须分页；表格使用项目封装的标准表格组件，不直接堆原生 `el-table`。
- 新增 / 编辑用弹窗，且抽成独立组件文件，与列表页解耦。
- 删除必须二次确认。
- 操作列固定为 **查看 / 编辑 / 删除**，按钮显隐由权限控制。
- 状态用 `el-tag` 展示。
- 下拉筛选选择后立即触发搜索，无须 blur / 点确认。

## 学生端 UI 约束

- 面向学习场景，使用卡片 / 列表 / 图表等布局；**禁止套用后台表格 UI**。
- 视频统一走项目封装的视频播放组件（内部已集成 HLS 与播放进度续播），不要重新引入第三方播放器。
- PC 优先；如确需移动端兼容，按需加媒体查询。

# 环境变量

- 后端域名、代理目标、超时时间、开发端口等差异化配置走 `VITE_*` 环境变量；禁止把这些值硬编码到代码里。
- 两个工程的 env 变量集合不完全相同，按各自 README / 配置文件维护。

# 禁止行为

- 禁止页面 / 组件直接 import axios，必须走统一的 request 实例。
- 禁止硬编码后端地址或绝对 URL。
- 禁止把接口请求逻辑写在 `views/` 里（必须放 `api/`）。
- 禁止单文件组件过大（推荐 500 行内）；超过则拆子组件 / 抽组合式函数。
- 禁止内联样式，统一用 SCSS / scoped 样式。
- 禁止学生端使用后台表格 UI；禁止管理后台引入移动端响应式方案。
- 禁止改动字段命名映射，必须与后端保持一致。

# 子工程约束

- `smart-campus-front-admin/AGENTS.md`：三段式、弹窗、二次确认、状态 Tag、列表必分页、页面拆组件、表单独立组件。
- `smart-campus-front-web/AGENTS.md`：面向用户、界面简洁、支持响应式、禁止套用后台表格 UI。

skills定义
vibe-coding/.claude/skills
java-module
vibe-coding/.claude/skills/java-module/SKILL.md
---
name: java-module
description: 为 Smart Campus 后端新增一个标准 CRUD 模块（PO + Mapper + Service + Biz + Controller + Query/DTO/VO 全套）。TRIGGER when 用户要求"新增一个 XX 模块 / 新增一张表的 CRUD / 加一套接口"。SKIP when 任务只是修改已有接口、调字段、修 bug。本 skill 是通用脚手架；项目业务规则（权限、登录、表关系等）请配合 `smart-campus-java` skill 使用。
---

# 适用前提

- 项目结构遵循 `smart-campus-java/CLAUDE.md`：admin / web / common 三模块，三套包路径（`com.smart.admin` / `com.smart.web` / `com.smart.campus`）。
- 持久层是**自定义泛型 Mapper**（不是 MyBatis Plus），所有 PO / Mapper / Service 落在 common 模块。
- 基础类（PO / Mapper / 简单 Service）通常由代码生成工具产出；本 skill 关注**新模块的边界、命名、归属与补全规则**。

# 上手前先确认三件事

1. **服务端**：这套接口面向管理端还是用户端？决定 Controller 与 Biz 写在 admin 还是 web 模块。
2. **表是否已存在**：表已存在 → 用工具生成 PO / Mapper / Service 后再补 Biz / Controller；表不存在 → 先评审表结构、写 DDL，再生成。
3. **是否复用现有领域**：若该业务与现有模块强相关（如附加一类课程数据），优先在原模块扩字段或加方法，不另起模块。

# 新模块涉及的文件清单

common 模块：

- PO：与表一一对应，放 `entity/po`。
- Query：列表查询参数，继承统一分页基类，放 `entity/query`。
- DTO：写操作入参，放 `entity/dto`；需要校验时用分组校验。
- VO：返回前端的数据结构，如果是简单返回可不单建 VO，直接返回 PO 列表；复杂结构（聚合 / 树形 / 关联展开）必须建 VO。
- Mapper：泛型接口 + XML 文件，XML 放 common 模块的 `resources/mappers/` 下。
- Service / ServiceImpl：接口与实现分两个包（`service` / `service.impl`）。

admin 或 web 模块（按服务端选其一）：

- Biz：业务编排类，命名 `XxxAdminBiz` / `XxxWebBiz`。
- Controller：入口类，命名 `XxxController`。

> 端专用 DTO / VO 也可以放在对应端模块的 `entity` 下，避免污染 common。

# 命名约定

- 类名以业务实体命名 + 角色后缀：`CourseInfo`（PO） / `CourseInfoQuery`（查询）/ `CourseSaveDTO`（写入）/ `CourseDetailVO`（详情返回）/ `CourseInfoMapper`（Mapper）/ `CourseInfoService`、`CourseInfoServiceImpl` / `CourseAdminBiz`、`CourseInfoController`。
- 路径名小驼峰且与模块对齐：`/api/courseInfo/loadDataList`、`/api/courseInfo/add`。
- 动作名优先用项目通用动词：`loadDataList`、`add`、`update`、`delete`、`detail`、`getXxxOptions`（下拉选项）、`getXxxTree`（树形数据）。

# 各层职责（必须遵守的边界）

- **Controller**：参数接收、参数校验、调用 Biz、返回统一响应。不写业务判断，不调 Mapper。
- **Biz**：业务编排。负责权限校验、跨 Service 调用组合、组装返回 VO、调用 Redis 组件等。
- **Service**：单领域业务逻辑，事务边界。简单 CRUD 可直接代理给 Mapper。
- **Mapper**：仅做单表 CRUD 或简单连表查询。复杂查询写在 XML。

# 参数与返回

- 列表查询用 Query 对象（继承分页基类），分页流程"先 count → 构造分页对象 → 查 list → 包成分页结果 VO"。
- 写操作用 DTO + `@RequestBody`，需要的字段加校验注解，分组场景用分组接口（创建 / 修改不同必填集）。
- Controller 一律返回统一响应包装类型，由公共基础 Controller 提供的成功 / 业务错误方法构造，不要 new 响应对象。
- 时间字段在 PO 上加统一的 JSON 格式化注解。

# 权限与登录

- 管理端 Controller 类级或方法级必须加权限注解，权限编码与系统菜单编码对齐。
- 当前登录用户从登录上下文取，不要在 Controller / Service 里手动解析 token。
- 涉及"教师只能操作自己课程"这类归属判定，归属校验放 Biz 层。

# 自检清单

- 包路径正确：PO / Service / Mapper 在 common，Controller / Biz 在 admin 或 web。
- 列表接口继承分页基类，统一走分页流程。
- 管理端 Controller 加了权限注解，编码与菜单表对齐。
- 没有循环里调 Mapper（N+1）。
- 时间字段加了统一的 JSON 格式化注解。
- 没有引入 MyBatis Plus API。
- Mapper XML 已落到 common 模块的 `resources/mappers/`。
- 没有把仅一端使用的类放进 common。
- 业务异常一律抛自定义业务异常，不在 Controller / Service catch 后吞掉。
- Controller 没有直接返回 PO 给前端的裸返；统一走响应包装。

# 与其他 skill 的分工

- 本 skill：**通用脚手架**（新模块要哪些文件、放哪个包、各层职责是什么）。
- `smart-campus-java` skill：**业务专项**（具体业务表、归属规则、Redis 组件复用等）。
- 涉及业务字段或权限编码时，两者配合使用。
vue-admin-page
vibe-coding/.claude/skills/vue-admin-page/SKILL.md
---
name: vue-admin-page
description: 在 Smart Campus 管理后台前端（smart-campus-front-admin）新增/改造一个标准三段式页面：搜索区 + 标准表格组件（含分页）+ 表单弹窗（新增/编辑/查看）。TRIGGER when 在 admin 工程里新增基础数据 / 教学业务 / 资源 / 系统设置类管理页。SKIP when 是学生端页面（用 `vue-web-page`）或与具体页面无关的全工程改造（路由、状态、请求层）。
---

# 适用前提

- 工程：`smart-campus-front-admin`，技术栈 Vue 3 + JS + Vite + Pinia + Element Plus + Sass。
- 三段式（强制）：**搜索区 → 表格 → 分页**；新增 / 编辑必须用弹窗；删除必须二次确认。
- 中文界面；状态列用 `el-tag`；下拉选择即触发搜索。

# 一个完整管理页对应的产物

- 列表页：`src/views/<业务子目录>/XxxManagement.vue`。
- 表单弹窗：`src/views/<业务子目录>/XxxFormDialog.vue`（与列表页同目录，独立文件）。
- 接口封装：`src/api/<模块>.js`。
- 路由 / 菜单配置：在路由配置与菜单配置文件里登记，`meta` 中带"是否需要登录"与"菜单编码"两项。

# 列表页结构（搜索区 → 表格 → 分页）

- **搜索区**：行内表单（`el-form` inline），常见控件为输入框、下拉、日期。下拉选择需绑定 `@change` 立即触发查询；输入框支持回车触发。提供"查询"与"重置"按钮。搜索条件用响应式对象统一管理，包含分页字段。
- **操作区**：搜索区下方放新增、批量操作、导入 / 导出等按钮。按钮按权限编码控制显隐。
- **表格区**：直接使用项目封装的标准表格组件（封装了 `el-table` + 分页 + 选中 + 排序）。
  - 列：业务字段 → 状态列（`el-tag`）→ 时间列 → 操作列（固定右侧）。
  - 操作列固定三个动作：**查看 / 编辑 / 删除**，按权限编码控制显隐。
- **分页区**：由标准表格组件内置，无需单独写。

# 表单弹窗结构

- 独立文件，prop 包含：显示开关、模式（创建 / 编辑 / 查看）、初始数据模型，以及业务下拉所需的选项数据（专业、班级等）。
- 事件：关闭（更新显示开关）、提交（通知父组件刷新列表）。
- 表单使用 `el-form` + 校验规则；规则定义在弹窗组件内部，与字段共维护。
- 查看模式整体只读（`disabled` 整表禁用），不显示底部"保存"按钮。
- 提交逻辑：先校验，再根据模式分别调用新增 / 修改接口，成功后弹消息并通知父组件。

# 接口封装

- 一个模块一个 api 文件，导出 `loadXxxList`、`addXxx`、`updateXxx`、`deleteXxx`、`getXxxDetail` 等业务方法。
- 接口请求统一走项目封装的 request 实例，不直接用 axios。
- 列表接口在 api 层做返回值兜底归一，确保上游拿到的总是统一的分页结构。

# 路由 / 菜单接入

- 路由 `meta.requiresAuth = true`。
- 路由 `meta.menuCode` 与后端菜单表的编码一致。
- 在菜单配置文件里登记，让侧边栏可以渲染。

# 权限控制

- 按钮级权限通过登录 store 暴露的"是否拥有菜单编码"方法控制 `v-if`。
- 字段级权限通常无需处理（统一在接口层控制返回字段）。
- 不要自定义 `v-permission` 指令。

# 提示与确认

- 信息提示统一走项目封装的消息工具，不直接调 `ElMessage`。
- 删除 / 批量操作走项目封装的确认工具，不直接调 `ElMessageBox`。
- 接口错误默认由响应拦截器统一弹窗；静默场景在调用时传参关闭弹窗。

# 自检清单

- 三段式齐全：搜索区 → 表格 → 分页。
- 新增 / 编辑独立成表单弹窗组件，不与列表页耦合。
- 删除走二次确认，成功后刷新列表。
- 状态列用 `el-tag`，操作列固定为"查看 / 编辑 / 删除"。
- 下拉选择立即触发查询，无须 blur 或点确认。
- 字段名与后端 PO / VO 完全一致；分页结果走统一兜底归一。
- 接口请求只走 api 文件，页面里没有 `axios` import。
- 不写内联样式；样式放 scoped 块。
- 按钮显隐走权限方法；菜单 `meta` 已配。

# 与其他 skill 的分工

- 本 skill：**怎么写一个 admin 管理页**（结构 + 组件职责 + 约束）。
- `smart-campus-front` skill：**前端工程入口与跨页面话题**（请求层、登录态、env、字段一致性）。
- `vue-web-page` skill：学生端页面。

vue-web-page
vibe-coding/.claude/skills/vue-web-page/SKILL.md
---
name: vue-web-page
description: 在 Smart Campus 学生端前端（smart-campus-front-web）新增/改造学习场景页面：我的课程 / 课程学习 / 在线考试 / 学习计划 / 学习分析 / 个人中心 / 消息中心 等。强调卡片式布局、复用项目视频播放组件、学习进度展示。TRIGGER when 在 web 工程里改/加面向学生的页面。SKIP when 是管理后台页面（用 `vue-admin-page`）或全工程级别改造。
---

# 适用前提

- 工程：`smart-campus-front-web`，技术栈 Vue 3 + JS + Vite + Pinia + Element Plus + Sass。
- 设计取向（见 `front-web/AGENTS.md`）：面向用户、界面简洁、支持响应式、**禁止套用后台表格 UI**。
- PC 优先；移动端按需加媒体查询，不强制全局响应式方案。

# 一个完整学生端页面对应的产物

- 业务页面：`src/views/<场景>/XxxPage.vue`（命名贴近场景，如 `MyCourse.vue` / `CourseStudy.vue` / `ExamList.vue`）。
- 二级交互：弹窗 / 抽屉抽成独立组件，与页面文件同目录。
- 接口封装：`src/api/<场景>.js`。
- 路由：在路由配置中登记，`meta` 标注是否需要登录。

# 业务页面布局原则

- **顶部头部区**：页面标题 + 搜索框 + 排序下拉。
- **筛选标签**：使用 `el-tabs`，常见 4 类：全部 / 进行中 / 已完成 / 未开始。
- **统计卡片**：横向多个统计卡，展示学习指标（已学课程、学习时长、平均成绩等）。
- **列表区**：使用**卡片网格**展示（封面、标题、教师、进度条、时长），**不要用 `el-table`**。
- **详情 / 学习页**：左右双栏（章节树 / 视频区）或上下结构。
- **移动端兼容**：用媒体查询把卡片网格堆叠为单列，重要按钮放大、不依赖鼠标 hover。

# 视频学习

- 视频统一走项目封装的视频播放组件（内部集成 HLS 与播放进度续播），**不要自己引入第三方播放器**。
- 进入课时页面时，从后端取该课时的最后播放时间点，传给播放组件作为初始播放位置。
- 播放过程中通过节流（建议 5 秒一次）调进度上报接口；接口请求设为静默错误，避免节流上报失败时打扰用户。

# 学习记录约定

- 学习进度字段命名与后端 PO / VO 一致，禁止前端起别名。
- 失败容忍：进度上报失败不影响学习体验，由后端通过 Redis 缓冲做最终一致。
- 切换课时 / 离开页面时主动上报一次最新进度，保证数据不丢。

# 接口封装

- 一个场景一个 api 文件，导出业务方法（如 `loadMyCourses`、`getCourseDetail`、`reportLessonProgress`）。
- 接口请求统一走项目封装的 request 实例。
- 列表接口在 api 层做返回值兜底归一。
- 静默场景（如进度上报、心跳）在调用时关闭错误弹窗。

# 提示与错误

- 信息提示走项目封装的消息工具。
- 错误优先在响应拦截器里统一弹；业务可按需关闭。
- 登录失效由拦截器自动跳转登录页，业务别重复处理。

# 自检清单

- 使用卡片 / 列表 / 图表，**没有 `el-table`**。
- 视频走项目封装的播放组件，没有引入第三方播放器。
- 字段名与后端 PO / VO 完全一致；分页结果走统一兜底归一。
- 接口请求只走 api 文件，页面里没有 `axios` import。
- 至少有一处媒体查询处理 PC → 移动端的差异。
- 错误提示统一走消息工具，登录失效不本地处理。
- 学习数据写入接口设为静默错误，避免节流上报弹错。
- 没有引入仅后台需要的依赖（如富文本编辑器、图表库等）。

# 与其他 skill 的分工

- 本 skill：**怎么写一个学生端业务页面**（结构 + 视频 + 学习进度）。
- `smart-campus-front` skill：**前端工程入口与跨页面话题**（请求层、登录态、env、字段一致性）。
- `vue-admin-page` skill：管理后台页面。
smart-campus-java
vibe-coding/.claude/skills/smart-campus-java/SKILL.md
---
name: smart-campus-java
description: Smart Campus 后端业务专项规则（课程 / 章节 / 课时 / 习题 / 试卷 / 考试 / 学习记录 / 资源 / 基础数据 / 权限菜单）。TRIGGER when 涉及具体业务（"在 admin 加课程审核接口" / "学生端拉取我的课程列表" / "学习进度记录" / "试卷自动评分"），需要清楚表关系、权限编码、登录态、Redis 组件用法。SKIP when 任务是纯脚手架式新增 CRUD（用 `java-module`）或与业务领域无关的纯通用问题。
---

# 适用范围

本 skill 假设你已经知道项目分层规范（详见 `smart-campus-java/CLAUDE.md`），重点提供**业务领域知识**与**归属判定规则**。

# 业务域 → 表的对应

- **基础数据**：院系、专业、班级、用户（含教师与学生，通过角色字段区分）。
- **课程结构**：课程主表 → 章节 → 课时 → 课时资源（4 级关联），课程归属一名教师。
- **选课**：通过"课程-班级"中间表与班级关联，学生通过所在班级自动获得课程访问权。
- **题库与试卷**：题目主表 + 题目选项；试卷主表 + "试卷-题目"中间表组装。
- **考试**：考试主表 + "考试-班级"中间表（按班级开考）。
- **作业 / 评估**：提交主表 + 提交题目明细表。
- **学习数据**：课程级进度、课时级进度（含视频播放位置）、学习日志（按时段写入）。
- **收藏**：用户与课程的收藏关联表。
- **资源**：统一的资源信息表（视频 / 文档），关联到课时。
- **学习计划**：计划主表 + 计划项明细表。
- **消息 / 通知**：系统通知 + 站内消息（消息主表 + 用户消息关联表）。
- **权限**：菜单表 + 角色菜单关联表。

实现接口前，先看 SQL 文件确认表结构，避免凭印象写字段。

# 角色边界（业务必须显式判定）

- 系统管理员：全部基础数据 + 教学业务 + 权限菜单 + 系统通知。
- 教师：只能管理自己名下课程（课程归属字段 = 当前登录用户 ID）；可创建章节 / 课时 / 作业 / 试卷 / 考试。
- 学生：通过班级访问课程；可学习课时、做作业 / 考试、记录学习进度。

**不能仅依赖前端隐藏按钮**——后端 Biz 层必须显式校验归属关系。

# 鉴权与登录态

- 管理端：登录拦截器 + 管理端登录 Redis 组件，结合权限注解做细粒度控制；权限编码与菜单表中编码对齐。
- 用户端：登录拦截器仅校验登录态，无细粒度权限。
- 当前登录用户从登录上下文持有器取，禁止自行解析 token。
- 无权限：抛业务异常（带权限错误码）。

# Redis 组件直接复用

公共 Redis 组件已提供以下场景能力，**不要重复造工具类**：

- 管理端 / 用户端登录态缓存。
- 学习进度的写入与聚合缓冲，避免对学习日志相关表的高频写。
- 大文件分片上传 session。
- 资源处理任务队列（视频转码、缩略图等异步任务）。

# 业务约束（实施细节）

## 课程

- 课程必须关联一名教师。非管理员修改 / 删除课程时，Biz 层必须校验"教师 ID = 当前登录用户 ID"。
- 删除课程要级联清理章节、课时、课时资源，以及该课程的学习进度数据。
- 选课走"课程-班级"中间表，不直接在学生与课程之间建关联。

## 题库 / 试卷 / 考试

- 客观题（单选 / 多选 / 判断）自动评分；主观题人工评分。评分逻辑放 Biz 层。
- 试卷通过"试卷-题目"中间表组装；同一题目可被多张试卷复用。
- 考试通过"考试-班级"中间表按班级开考。

## 学习记录

- 学习时长：按时段写入学习日志，再聚合到课程级与课时级进度表。
- 视频续播：课时级进度表中保存最后播放时间点，前端按 lessonId 取值续播。
- 写入路径优先经 Redis 缓冲后异步落库，避免高并发写库。

## 资源

- 上传走分片 session（Redis 组件提供）+ 异步任务队列处理。
- 视频字段（URL、HLS 索引、时长等）命名稳定，前端依赖，禁止改名。

## 消息 / 通知

- 系统通知与站内消息都走"消息主表 + 用户消息关联表"两层结构，方便按用户查询未读 / 已读。

# 接口命名

- 模块名小驼峰，对应主业务实体：`courseInfo`、`courseChapter`、`examInfo`、`paperInfo`、`questionInfo`、`resourceInfo`、`studyPlan`、`systemNotice` 等。
- 动作：`loadDataList`、`add`、`update`、`delete`、`detail`、`getXxxOptions`（下拉）、`submitAnswer`（提交答案）等。
- 完整路径形如：`/api/<模块>/<动作>`（`/api` 由 context-path 提供）。

# 字段一致性自检

- 后端字段命名与前端 API 文件调用保持一致。
- 列表分页结果字段固定（总数 / 页码 / 页大小 / 列表数组）。
- 时间字段统一字符串格式，不返回时间戳。

# 检查清单（业务专项）

- 课程 / 试卷 / 考试操作是否校验了主从归属关系。
- 教师视角接口是否过滤"教师 ID = 当前登录用户"。
- 学生视角接口是否按"班级 → 课程"链路过滤。
- 管理端接口权限编码与菜单表是否一致。
- 学习记录写入是否走了 Redis 缓冲。
- 资源类接口是否复用现成的 Redis 组件。

# 与 java-module 的分工

- 新增一整套 CRUD 模块 → 用 `java-module` 生成骨架，再回到本 skill 套业务规则。
- 改既有业务接口 / 加细分动作 → 直接看本 skill 的领域映射，不用走 `java-module`。
smart-campus-front
vibe-coding/.claude/skills/smart-campus-front/SKILL.md
---
name: smart-campus-front
description: Smart Campus 前端工程入口与跨页面话题：请求层封装、登录与权限态、环境变量与代理、字段一致性原则、admin 与 web 两个工程的差异。TRIGGER when 涉及登录登出、请求 / 响应拦截器、axios 实例、路由守卫、菜单权限、env 配置、proxy、字段对齐策略等"跨多个页面 / 工程级"话题。SKIP when 任务只是写单个页面——管理后台页面用 `vue-admin-page`，学生端页面用 `vue-web-page`。
---

# 工程定位

两个独立工程：

- **smart-campus-front-admin**：管理后台，服务管理员 / 教师。token header 名 `adminToken`，代理目标为管理端后端服务。
- **smart-campus-front-web**：学生端，服务学生。token header 名 `studentToken`，代理目标为用户端后端服务。

两个工程共享技术栈与目录约定，差异主要在 token header、角色权限、UI 走向（详见 `smart-campus-front/CLAUDE.md`）。**两个工程之间不共享代码**。

# 关键模块

每个工程都应有以下几块"公共基建"：

- **请求封装**：统一的 axios 实例 + 请求 / 响应拦截器。
- **token 工具**：与 localStorage 同步的读 / 写 / 清三个函数。
- **登录 store**：Pinia 中的 auth store，保存 token、用户信息、菜单树、菜单编码列表，并暴露"是否拥有菜单编码"的判断方法。
- **路由配置**：路由表 + 守卫；管理端再多一个菜单配置文件。
- **消息 / 确认工具**：对 `ElMessage` / `ElMessageBox` 的统一封装，避免散落。
- **业务通用工具**：日期格式化、文件大小格式化、字符串处理等。

# 请求层规范

- **baseURL**：固定 `/api`；生产环境可由 `VITE_*` 环境变量拼接外部域名前缀。
- **超时**：默认 10 秒；通过环境变量可调（推荐 web 工程暴露环境变量，admin 工程可写死）。
- **请求拦截器**：从登录态读 token，写入对应 header（管理端 / 用户端 header 名不同）。
- **响应拦截器**：
  - 业务码成功：直接返回业务数据；
  - 登录失效码：清登录态 + 跳转登录页（带 `redirect` 查询参数），**业务页面不要重复处理**；
  - 其他业务错误：默认弹错；调用方可通过参数（如 `showError: false`）关闭弹窗。
- **错误兜底**：网络异常 / 超时统一弹"网络异常"。
- **列表返回兜底**：建议在 api 文件里做归一化，确保上游拿到的总是统一的分页结构（总数 / 页码 / 页大小 / 列表数组）。

# 登录态规范

- 登录成功：调用 store 的登录 action → 后端返回 `{ token, userInfo, menuList }` → 写入 store + localStorage。
- 刷新页面恢复：在路由守卫里检测到有 token 但无 userInfo 时，调用 store 的"拉取登录信息"action 重新加载。
- 登出：清 store + 清 localStorage + 跳转登录页。
- 登录失效与未登录跳转，**只在响应拦截器里发生一次**，业务代码不重复处理。

# 路由与权限

- 路由 `meta` 约定两个字段：是否需要登录（默认 true）、菜单编码。
- 守卫流程：未登录跳登录页 → 已登录但无用户信息时拉取 → 校验菜单编码 → 通过则放行。
- 按钮级权限：通过登录 store 暴露的"是否拥有菜单编码"方法控制 `v-if`，**不**自定义 `v-permission` 指令。
- 学生端只校验登录，不校验菜单编码。

# 环境变量

每个工程在 `.env.development` / `.env.production` 中按需声明：

- 后端域名前缀（生产环境）；
- 接口 baseURL（默认 `/api`，特殊场景可调）；
- 请求超时；
- 开发端口；
- 开发代理目标（指向对应后端服务的本地端口）。

禁止把后端地址 / 端口硬编码进代码。所有跨环境差异都走 `import.meta.env.VITE_*`。

# 字段一致性原则

- 接口字段名严格沿用后端 PO / VO（驼峰），如 `courseId` / `teacherId` / `createTime` / `studyDuration` / `playTime`。
- 列表返回结构固定（总数 / 页码 / 页大小 / 列表数组），api 层做兜底归一。
- 时间字段统一字符串 `yyyy-MM-dd HH:mm:ss`，前端按需用日期库解析；**禁止前端额外加格式化逻辑去"修复"后端时间**。
- 枚举值（状态、角色类型等）保持后端定义，禁止前端自造同义词。

# 工程级开发流程

1. 确认任务对象：
   - 单页改造 / 新页面 → 转 `vue-admin-page` 或 `vue-web-page`。
   - 请求层 / 鉴权 / 路由 / 菜单 / env / 跨页面公共逻辑 → 留在本 skill。
2. 改请求层：先在 request 文件里调整，再回头检查所有调用方是否受影响。
3. 改登录态：token 工具、登录 store、路由守卫三处必须同步。
4. 增菜单 / 路由：管理端在路由 + 菜单配置文件登记，同步在后端菜单表对齐编码。
5. 引入新依赖：先确认对端是否已有同类依赖（admin / web 互不混引）；视频统一一个播放组件，富文本仅管理端使用。

# 自检清单（跨页面话题专属）

- 业务页面没有直接 `import axios`，全部走统一 request 实例。
- 没有在多个地方手写 token header；仅请求拦截器一处统一注入。
- 没有在业务页面手动跳转登录页；登录失效统一由响应拦截器处理。
- 环境差异通过 `import.meta.env.VITE_*` 控制，不写死域名 / 端口。
- 新增菜单时同步配 `meta.menuCode` 与后端菜单表。
- admin 页面用项目封装的标准表格组件；web 页面用卡片 + 项目封装的视频播放组件。

# 与其他 skill 的分工

- 本 skill：**跨页面 / 工程级**（请求、登录、路由、env、字段约定）。
- `vue-admin-page`：admin 单页面结构与三段式实现。
- `vue-web-page`：web 单页面结构与学习场景实现。
- 涉及具体页面时，本 skill 提供"环境与登录上下文"，单页面 skill 提供"页面结构"。

settings.json
vibe-coding/.claude/settings.json
{
  "customSkills": [
    ".claude/skills/java-module.md",
    ".claude/skills/vue-admin-page.md",
    ".claude/skills/vue-web-page.md",
    ".claude/skills/smart-campus-java.md",
    ".claude/skills/smart-campus-front.md"
  ],
  "projectContextFile": "CLAUDE.md",
  "autoLoadSkills": true
}
