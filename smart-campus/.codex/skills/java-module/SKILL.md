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