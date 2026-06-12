# 需求实施计划

- [x] 1. 初始化后端工程骨架并建立核心边界
  - 创建 FastAPI 服务目录、应用入口、配置模块和基础错误响应结构，对应 `requirements.md` 中 Requirement 7 和 `design.md` 中 Backend API 约束
  - 建立 SQLite 初始化逻辑、环境变量读取和健康检查接口，对应 `design.md` 中 Delivery Plan 1 和 Error Handling

- [x] 2. 实现数据模型与存储层
  - 创建 `feedback_items`、`draft_batches`、`draft_batch_items`、`drafts`、`submissions` 的模型与 Repository，对应 `design.md` 中 Data Models 和 Correctness Properties
  - 实现 `related_id` 校验、状态枚举和时间字段统一处理，对应 `requirements.md` 中 Requirement 1、Related Identifier Rule 和 `backend-schema.md`
  - [x]* 2.1 为模型校验和 Repository 编写单元测试
    - 覆盖 `related_id` 格式、状态流转、唯一归属等规则，对应 `design.md` 中 Test Strategy

- [x] 3. 实现用户反馈与已提交 Issue 查询接口
  - 实现 `POST /api/feedback`、`GET /api/issues/submitted`、`GET /api/issues/submitted/search`，对齐 `api-contract.md` 和 `requirements.md` 中 Requirement 1、Requirement 2
  - 实现列表排序、筛选和重复 `related_id` 查询逻辑，对应 `requirements.md` 中 Requirement 2 和 `design.md` 中 User Submission Page
- [x]* 3.1 为用户接口编写单元测试和接口测试
    - 覆盖表单校验、搜索结果、倒序排序和重复提示数据来源，对应 `design.md` 中 Test Strategy

- [x] 4. 检查点 - 确保所有测试通过,如有疑问请询问用户
  - 验证后端骨架、数据层和用户侧接口可运行

- [x] 5. 实现管理员反馈列表和批次创建流程
  - 实现 `GET /api/feedback` 和 `POST /api/draft-batches`，支持待处理列表、批次创建、`related_id` 分布和混合确认，对应 `requirements.md` 中 Requirement 3 和 `design.md` 中 Admin Console
  - 将已入批次的反馈标记为 `grouped`，保证未完成批次的唯一归属，对应 `design.md` 中 Correctness Properties
  - [x]* 5.1 为批次创建和混合 `related_id` 规则编写单元测试
    - 覆盖空批次、重复分组、确认缺失等场景，对应 `api-contract.md` 和 Error Handling

- [x] 6. 实现 Draft 生成与编辑流程
  - 实现 `POST /api/draft-batches/{id}/integrate`、`GET /api/drafts/{id}`、`PUT /api/drafts/{id}`，对齐 `requirements.md` 中 Requirement 4、Requirement 5
  - 建立 AI service 接口、Prompt 组装、Draft 固定模板生成和失败落库逻辑，对应 `design.md` 中 AI Integration Service 和 GitHub Issue Template
  - [x]* 6.1 为 Draft 生成和更新流程编写单元测试
    - 覆盖缺失信息占位、草稿更新、失败状态写回，对应 `design.md` 中 Test Strategy

- [x] 7. 实现 GitHub 提交流程与状态回写
  - 实现 `POST /api/drafts/{id}/submit`、GitHub client、提交结果落库、反馈和批次状态同步，对应 `requirements.md` 中 Requirement 6 和 `design.md` 中 GitHub Submission Service
  - 实现相同 `related_id` 限频和服务端 Token 读取，对应 `requirements.md` 中 Requirement 7
  - [x]* 7.1 为提交流程编写单元测试和接口测试
    - 覆盖成功回写、失败保留草稿、限频命中、Token 缺失，对应 `design.md` 中 Error Handling

- [x] 8. 初始化 Vue 前端工程并配置开发联调环境
  - 创建 `Vue 3 + Vite + Vue Router` 工程结构、全局样式 token、页面路由和 API service，对应 `frontend-vue-plan.md` 和 `frontend-style.md`
  - 在 `vite.config.ts` 中配置 `allowedHosts` 和 `/api` 反向代理，对应 `frontend-vue-plan.md` 中 Vite Configuration 和平台规则

- [x] 9. 实现用户提交页
  - 完成历史 Issue 列表、搜索筛选、重复 `related_id` 提示和反馈表单，对应 `frontend-vue-plan.md` 中 `UserHomePage.vue` 和 `requirements.md` 中 Requirement 1、Requirement 2
  - 落实克制专业视觉风格、任务导向文案和轻量交互，对应 `frontend-style.md` 和 `frontend-vue-plan.md` 中 Anti AI-Look Rules
- [x]* 9.1 为用户页交互编写组件测试
    - 覆盖表单校验、重复提示显示、列表筛选，对应 `design.md` 中 Test Strategy

- [x] 10. 实现管理员工作台页面
  - 完成待处理反馈表格、批次摘要、`related_id` 分布、Draft 编辑器和历史 Issue 参考区，对应 `frontend-vue-plan.md` 中 `AdminWorkbenchPage.vue`
  - 接入批次创建、Draft 生成、Draft 更新和 GitHub 提交接口，对应 `requirements.md` 中 Requirement 3、Requirement 4、Requirement 5、Requirement 6
- [x]* 10.1 为管理员页面编写组件测试
  - 覆盖批次选择、混合确认、Draft 编辑和提交结果显示
- [x]* 10.2 管理员工作台成品化重构
    - 将后台页重构为左侧收件箱导航、中栏聚合审阅台、右侧草稿编辑器三栏结构
    - 完成收件箱式时间分组队列、审阅判断区、固定动作带、草稿状态条与编辑器面板
    - 补齐三栏自动聚焦、滚动联动和新增页面断言，保持工作台演示链路稳定

- [x] 11. 检查点 - 确保所有测试通过,如有疑问请询问用户
  - 验证前后端联调通过，关键接口和页面交互可运行

- [x] 12. 启动本地预览并整理部署产物
  - 启动后端服务和 Vite 前端预览，确认用户页和后台页可访问，对应 `dev-workflow.md` 中 Preview Strategy
  - 构建前端 `dist/` 产物并确认可压缩上传，对应 `frontend-vue-plan.md` 中 Build and Deploy Flow
- [x]* 12.1 持续回归验证工作台重构
    - 在三栏工作台连续重构后重复执行 `npm test` 与 `npm run build`，确保交互与构建稳定
- [x]* 12.2 生成可上传的静态交付包
    - 已将 `frontend/dist/` 打包为 `frontend/issue-aggregator-frontend-dist.zip`，可直接用于静态托管上传
    - 已核对压缩包内容仅包含 `dist/index.html` 与 `dist/assets/*` 静态产物
