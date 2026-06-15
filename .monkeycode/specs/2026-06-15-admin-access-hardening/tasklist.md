# 需求实施计划

- [ ] 1. 扩展后台安全配置与启动校验
  - 在 `backend/app/config.py` 增加管理员账号、密码摘要、会话密钥、Cookie 参数、会话时长、登录失败窗口、冷却时长、后台随机前端路由等配置，对应 `requirements.md` 中 Requirement 1、Requirement 2、Requirement 3、Requirement 4
  - 为生产环境增加关键安全配置缺失或格式非法时的启动失败校验，对应 `requirements.md` 中 Requirement 4.4 和 `design.md` 中 Configuration Failures
  - [ ]* 1.1 为安全配置解析和生产环境启动校验编写单元测试
    - 覆盖默认值、随机 slug 格式校验、关键密钥缺失和非法配置场景，对应 `design.md` 中 Test Strategy

- [ ] 2. 实现后台登录尝试与会话存储模型
  - 在 `backend/app/database.py` 和相关模型、仓储文件中新增 `admin_sessions`、`admin_login_attempts` 表及对应数据访问逻辑，对应 `requirements.md` 中 Requirement 2、Requirement 3 和 `design.md` 中 Data Models
  - 实现 session token 哈希存储、会话查询、续期、撤销、登录失败计数与冷却判断，对应 `design.md` 中 Session Repository 和 Correctness Properties
  - [ ]* 2.1 为会话仓储和登录尝试仓储编写单元测试
    - 覆盖 token 哈希查找、空闲过期、绝对过期、撤销状态、冷却窗口和成功失败计数，对应 `design.md` 中 Correctness Properties 与 Backend Tests

- [ ] 3. 实现后台认证服务与会话校验依赖
  - 新增管理员密码校验、登录冷却判定、会话创建、会话读取、登出撤销等服务逻辑，对应 `requirements.md` 中 Requirement 1、Requirement 2、Requirement 3
  - 将现有 `require_admin_token` 迁移为 `require_admin_session`，并保持现有后台审计事件与操作日志链路可复用，对应 `requirements.md` 中 Requirement 6.2 和 `design.md` 中 Admin Session APIs
  - [ ]* 3.1 为后台认证服务编写单元测试
    - 覆盖密码错误、冷却命中、登录成功、会话失效、登出撤销和统一认证失败响应，对应 `design.md` 中 Authentication Failures

- [ ] 4. 暴露后台登录、会话探测与登出接口
  - 在现有后台 API 命名空间下新增 `session/login`、`session/me`、`session/logout` 接口，并返回后台工作台所需的最小管理员信息和会话过期信息，对应 `requirements.md` 中 Requirement 1、Requirement 2、Requirement 5
  - 保持公开反馈接口和公开已提交 Issue 查询接口继续匿名可用，对应 `requirements.md` 中 Requirement 6.4
  - [ ]* 4.1 为后台认证接口编写接口测试
    - 覆盖成功登录、错误密码、冷却锁定、有效会话探测、登出后失效和受保护接口拒绝匿名访问，对应 `design.md` 中 Backend Tests

- [ ] 5. 将后台业务接口切换到会话鉴权
  - 把现有反馈列表、建批、草稿生成、草稿保存、Issue 提交、审计查询等后台接口统一接到会话鉴权依赖，对应 `requirements.md` 中 Requirement 2.1、Requirement 6.1
  - 保留现有 `admin_auth_failed`、`admin_action_succeeded` 审计行为，并补齐登录成功、登出或会话撤销事件，对应 `requirements.md` 中 Requirement 3.4、Requirement 3.5
  - [ ]* 5.1 为受保护后台接口补回归测试
    - 覆盖有效会话下业务接口可用、失效会话被拒绝、会话撤销后重新登录恢复，对应 `design.md` 中 Backend Tests

- [ ] 6. 前端切换为 Cookie 会话认证模式
  - 修改 `frontend/src/services/api.ts`，删除 `sessionStorage.issueAggregatorAdminToken` 和 `X-Admin-Token` 逻辑，统一对后台请求启用 `credentials: 'include'`，对应 `requirements.md` 中 Requirement 5.4 和 `design.md` 中 Frontend Admin Access Flow
  - 修改 `frontend/src/pages/AdminWorkbenchPage.vue`，将后台登录页从 token 输入改为用户名密码表单，并在首屏先调用 `session/me` 决定是否解锁工作台，对应 `requirements.md` 中 Requirement 1、Requirement 5
  - [ ]* 6.1 为前端后台认证流程编写组件测试
    - 覆盖会话探测成功、未登录显示表单、登录失败提示、登出回退和鉴权失败后重置界面，对应 `design.md` 中 Frontend Tests

- [ ] 7. 将后台前端路由切换为随机路由配置
  - 修改 `frontend/src/router/index.ts`，通过 `VITE_ADMIN_ROUTE_SLUG` 注册后台工作台路由，并保持公开导航继续不暴露后台入口，对应 `requirements.md` 中 Requirement 4.2、Requirement 4.5
  - 对齐前后端环境变量命名和本地开发配置路径，确保前端后台路由与后端 API namespace 可分别配置，对应 `requirements.md` 中 Requirement 4.1、Requirement 6.3
  - [ ]* 7.1 为动态后台路由注册编写前端测试
    - 覆盖动态 slug 注册、生效访问和旧 `/admin` 路径不再直达后台页，对应 `design.md` 中 Frontend Tests

- [ ] 8. 检查点 - 确保所有测试通过,如有疑问请询问用户
  - 验证安全配置、后台会话、随机路由和现有工作台主链路可协同工作

- [ ] 9. 补充自动化回归与端到端脚本
  - 为后台登录成功、错误密码冷却、会话恢复、登出失效和随机路由访问补充自动化回归脚本，对应 `requirements.md` 中 Requirement 2、Requirement 3、Requirement 4、Requirement 5
  - 复用现有管理流 E2E 思路，保证建批、草稿和提交在新认证模型下继续可用，对应 `requirements.md` 中 Requirement 6.1
  - [ ]* 9.1 为安全升级新增端到端测试夹具与辅助工具
    - 提供登录态初始化、Cookie 注入、过期会话模拟和冷却窗口构造工具，对应 `design.md` 中 End-to-End Checks

- [ ] 10. 检查点 - 确保所有测试通过,如有疑问请询问用户
  - 重跑后端单元测试、前端组件测试、前端构建和后台安全回归脚本，确认本轮切换完成
