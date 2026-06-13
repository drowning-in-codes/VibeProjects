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