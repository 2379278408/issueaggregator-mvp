# Issue Aggregator 架构说明

## 1. 系统目标

Issue Aggregator 用于接收用户反馈、在后台对反馈进行聚合整理、生成 Issue 草稿并提交到 GitHub，同时保留审计轨迹。

## 2. 运行结构

项目由三部分组成：

- `frontend/`: Vue 3 + Vite 单页应用
- `backend/`: FastAPI + SQLite 服务
- `backend/data/*.db`: SQLite 数据文件，默认按环境分流

本地开发时由 Vite 反向代理 `/api` 到 FastAPI；在线预览或容器部署时仍保持单入口访问模型。

## 3. 前端结构

前端入口位于 `frontend/src/main.ts`，加载路由和四个样式层：

- `tokens.css`: 设计令牌
- `base.css`: 基础样式
- `layout.css`: 布局层
- `components.css`: 组件样式合集

核心页面：

- `UserHomePage.vue`: 公开提交页，负责反馈输入、关联标识查重、历史 Issue 浏览
- `AdminWorkbenchPage.vue`: 管理工作台，负责登录态、队列、建批、草稿和提交链路
- `NotFoundPage.vue`: 404 页面

核心组件：

- `AppShell.vue`: 页面框架、顶部导航、全局 Toast 注入点
- `AdminLoginCard.vue`: 后台登录卡片
- `FeedbackQueue.vue`: 反馈队列
- `ReviewPanel.vue`: 审阅和建批辅助面板
- `DraftEditor.vue`: 草稿编辑区
- `AuditPanel.vue`: 审计事件面板
- `ToastNotification.vue`: 全局通知
- `SkeletonLoader.vue`: 骨架屏

## 4. 后端结构

后端入口位于 `backend/app/main.py`：

- 应用启动时初始化数据库表结构
- 注入安全响应头
- 注册公开、会话、管理和健康检查路由
- 将异常统一转换成结构化 envelope

核心模块：

- `config.py`: 环境变量加载与配置校验
- `database.py`: SQLite 连接、建表和轻量迁移
- `auth.py`: 会话哈希、密码校验、来源 IP 解析、登录冷却、审计写入
- `responses.py`: 成功/失败响应 envelope
- `repositories.py`: 数据访问与业务服务层
- `routers/feedback.py`: 主要业务 API
- `routers/health.py`: 健康检查

## 5. 数据模型

SQLite 里当前维护 8 张核心表：

- `feedback_items`: 原始反馈
- `draft_batches`: 草稿批次
- `draft_batch_items`: 批次与反馈映射
- `drafts`: 生成或编辑中的草稿
- `submissions`: GitHub 提交结果
- `public_feedback_ip_limits`: 公开反馈按 IP 日限流
- `audit_events`: 管理行为与认证审计
- `admin_sessions`: 后台登录会话
- `admin_login_attempts`: 登录失败和冷却统计

`initialize_database()` 会在启动时执行建表，并确保 `feedback_items` 的增量字段存在。

## 6. 核心业务流

### 6.1 公开提交流

1. 用户在公开页提交反馈。
2. 后端校验 `type`、`related_id` 和内容。
3. 后端执行来源校验、重复窗口校验、日限流校验。
4. 反馈写入 `feedback_items`，状态进入待处理。
5. 前端可查询已提交 Issue 历史和关联标识查重结果。

### 6.2 管理工作台流

1. 管理员通过用户名密码登录。
2. 后端签发 session cookie，并记录认证审计。
3. 工作台拉取 `pending/grouped/submitted` 队列。
4. 管理员勾选反馈并创建批次。
5. 后端整合批次并生成草稿。
6. 前端允许人工编辑后保存草稿。
7. 草稿提交到 GitHub，相关反馈转入已提交状态。
8. 审计面板可回看认证失败和成功操作事件。

## 7. 安全边界

当前实现包含以下安全措施：

- FastAPI 文档页默认关闭，只有 `ENABLE_API_DOCS=true` 时开放
- 后台以 session cookie 为主认证方式
- 登录失败进入冷却窗口
- 公开反馈按来源 `Origin` 和 IP 做保护
- API 响应附带 `X-Frame-Options`、`Content-Security-Policy` 等安全头
- 审计事件写入数据库，便于回看关键操作
- 密码哈希已采用 `bcrypt`，同时兼容旧 SHA-256 哈希过渡

## 8. 当前架构结论

这套架构已经满足 MVP 的功能闭环和持续演进要求。当前主要技术债集中在两个超大页面文件和一个超大样式文件的拆分，而不是底层能力缺失。
