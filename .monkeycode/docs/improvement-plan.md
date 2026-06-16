# 项目优化完善计划

基于 2026-06-16 全面审查，列出 19 项优化点，按类别与优先级排列。供其他模型或开发者按序推进。

---

## A. 安全性（优先处理）

### A-1. 密码哈希从 SHA-256 迁移到 bcrypt/argon2

- 严重程度: 高
- 现状: `backend/app/auth.py:81` 直接使用 `hashlib.sha256(password.encode()).hexdigest()` 做密码哈希，无盐值，无法对抗彩虹表攻击。
- 目标:
  - 引入 `bcrypt`（推荐）或 `argon2-cffi` 依赖
  - 替换 `hash_password` / `verify_admin_password` 中的 `sha256` 调用
  - 向后兼容：提供一次性从 SHA-256 哈希迁移到 bcrypt 的逻辑（登录成功时自动 rehash 并更新配置）
- 实现提示:
  ```python
  import bcrypt
  def hash_password(password: str) -> str:
      return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
  def verify_password(password: str, stored: str) -> bool:
      return bcrypt.checkpw(password.encode(), stored.encode())
  ```
- 涉及文件: `backend/app/auth.py`、`backend/app/config.py`、`backend/.env`、`backend/requirements.txt`

### A-2. auth.py 补充专属单元测试

- 严重程度: 高
- 现状: `auth.py` 中 `hash_session_token`、`verify_admin_password`、`verify_admin_credentials`、`_resolve_client_ip`、`_write_audit_event`、`_parse_client_ip`、`_normalize_client_ip` 均无直接单元测试，仅在 `test_api.py` 和 E2E 中间接覆盖。
- 需覆盖的边界条件:
  - `hash_session_token`: 空字符串、超长 token、确定性（相同输入相同输出）
  - `verify_admin_password`: 空密码、错误密码、未配置密码哈希的情况
  - `verify_admin_credentials`: 用户名不匹配、密码不匹配、两者都不匹配、均匹配
  - `_resolve_client_ip`: `X-Forwarded-For` 单 IP、多 IP（取最左）、无代理头直连、私有 IP 回退、`HTTP_X_FORWARDED_FOR` 备选头、无可用 IP
  - `_write_audit_event`: 写事件成功、数据库不可用时的容错
- 目标文件: `backend/tests/test_auth.py`（新建）

---

## B. 测试补齐

### B-1. config.py 补齐配置字段测试

- 严重程度: 中
- 现状: `backend/tests/test_config.py` 仅覆盖 `_default_database_url` 的分环境分流逻辑（3 个测试），其余 22 个配置字段和 4 个校验函数均无测试。
- 需覆盖:
  - `_require_env`: 环境变量存在时返回、不存在时抛 `SystemExit`
  - `_validate_admin_route_slug`: 合法值通过（8 位/64 位）、过短拒绝、过长拒绝、含非法字符拒绝、空字符串、大写字母
  - `_production_required`: 缺 `ADMIN_USERNAME` 时抛异常、缺 `ADMIN_PASSWORD_HASH` 时抛异常、全部存在时通过
  - `_load_env_file`: `.env` 存在时加载、不存在时跳过
  - CSV 白名单解析: 单域名、多域名、空字符串、含空格的解析
  - 默认值验证: `API_BASE_PATH`、`MAX_FEEDBACK_CONTENT_LENGTH`、`MAX_RELATED_ID_LENGTH`、`PUBLIC_FEEDBACK_DAILY_IP_LIMIT`、`ADMIN_SESSION_IDLE_MINUTES`、`ADMIN_SESSION_MAX_MINUTES`、`ADMIN_LOGIN_COOLDOWN_MINUTES`、`ADMIN_MAX_LOGIN_ATTEMPTS`、`RATE_LIMIT_PER_HOUR` 等
- 目标文件: `backend/tests/test_config.py`（扩展）

### B-2. main.py 应用层测试

- 严重程度: 中
- 现状: FastAPI 生命周期（数据库初始化）、安全响应头中间件、异常处理器无直接单元测试。异常处理器和安全头在 `test_api.py` 中通过 HTTP 层面间接验证。
- 需覆盖:
  - 安全头中间件: 响应中是否包含 `Content-Security-Policy`、`X-Frame-Options: DENY`、`X-Content-Type-Options: nosniff`、`Referrer-Policy`、`Strict-Transport-Security`、`X-XSS-Protection`
  - `RequestValidationError` 异常处理器: 返回 422、响应体含 `error_code` 和 `message`
  - `HTTPException` 异常处理器: 透传状态码和响应体
  - 启动事件: 数据库文件不存在时自动创建并初始化表
  - 根路径 `/` 返回 404
- 目标文件: `backend/tests/test_main.py`（新建）

### B-3. responses.py 工具函数测试

- 严重程度: 低
- 现状: `success_response(data)` 和 `error_response(error_code, message)` 无测试。
- 目标: 验证返回字典结构 `{status, data}` 和 `{status, error: {code, message}}` 格式正确。
- 目标文件: `backend/tests/test_responses.py`（新建）

### B-4. 前端引导代码测试

- 严重程度: 低
- 现状: `frontend/src/main.ts`（应用引导）和 `frontend/src/App.vue`（根组件）无测试。
- 目标: 快照测试验证 `createApp` 挂载成功、`App.vue` 包含 `<RouterView />`。
- 目标文件: `frontend/src/App.test.ts`（新建）

---

## C. 代码结构与可维护性

### C-1. AdminWorkbenchPage.vue 组件拆分（1722 行）

- 严重程度: 高
- 现状: 单个 Vue 文件包含登录表单、三栏工作台（待处理/已分组/已提交队列）、主题画布审阅面板、草稿编辑器、GitHub 提交区、审计事件查看器全部逻辑。认知负担大，测试粒度粗。
- 建议拆分为以下独立组件:
  ```
  src/components/admin/
    AdminLoginCard.vue          -- 登录表单 + 冷却提示
    FeedbackQueue.vue            -- 队列选择器 + 反馈卡片列表 + 一键勾选
    ReviewPanel.vue              -- 主题画布 + 证据卡片 + 审阅决策
    DraftEditor.vue              -- 草稿标题/正文编辑 + 保存 + 预览
    BatchInsight.vue             -- 批次统计网格
    AuditPanel.vue               -- 审计事件列表 + 筛选器
    SubmissionChecklist.vue      -- 提交前检查清单
  ```
- 约束: 拆分后 AdminWorkbenchPage.vue 仅负责状态协调与子组件通信，不保留业务逻辑。
- 涉及文件: `frontend/src/pages/AdminWorkbenchPage.vue`、`frontend/src/pages/AdminWorkbenchPage.test.ts`
- 测试: 拆分后子组件各自补充独立测试。

### C-2. components.css 按模块拆分（3071 行）

- 严重程度: 中
- 现状: 单个 CSS 文件超过 3000 行，涵盖所有组件样式，按 BEM 风格编写但无文件级隔离。
- 建议拆分:
  ```
  src/styles/
    tokens.css            -- 已有
    base.css              -- 已有
    layout.css            -- 已有
    auth.css              -- 登录卡片样式
    queue.css             -- 队列/信号流卡片样式
    review.css            -- 主题画布/审阅面板样式
    draft-editor.css      -- 草稿编辑器/批次网格样式
    audit.css             -- 审计面板样式
    feedback-form.css     -- 公开提交表单样式
    history.css           -- 已提交 Issue 历史浏览器样式
  ```
- 涉及文件: `frontend/src/styles/components.css`

### C-3. UserHomePage.vue 组件拆分（950 行）

- 严重程度: 中
- 现状: 反馈表单、关联 ID 查重面板、快捷模板、已提交通知、已提交 Issue 历史浏览器混在同一文件。
- 建议拆分为:
  ```
  src/components/public/
    FeedbackForm.vue             -- 类型选择 + 描述 + 关联 ID 输入 + 提交
    DuplicateCheckPanel.vue      -- 查重结果展示
    QuickTemplates.vue           -- 快捷模板 chips
    SubmittedHistory.vue         -- 已提交 Issue 列表 + 筛选
    SubmissionSuccessNotice.vue  -- 提交成功通知栏
  ```
- 涉及文件: `frontend/src/pages/UserHomePage.vue`、`frontend/src/pages/UserHomePage.test.ts`

---

## D. 功能完整性

### D-1. 添加 404 页面

- 严重程度: 中
- 现状: 不存在路由访问时浏览器仅返回空白页，无任何提示。
- 目标:
  - 新建 `frontend/src/pages/NotFoundPage.vue`，含返回首页链接
  - 在 `frontend/src/router/index.ts` 注册 `/:pathMatch(.*)*` 通配路由
  - 补充 `frontend/src/pages/NotFoundPage.test.ts` 验证渲染和返回链接
- 实现提示:
  ```vue
  <template>
    <div class="not-found">
      <h1>页面不存在</h1>
      <p>您访问的路径不存在，请检查链接是否正确。</p>
      <router-link to="/">返回首页</router-link>
    </div>
  </template>
  ```

### D-2. 全局错误提示机制（Toast/通知）

- 严重程度: 中
- 现状: 前端 API 调用失败时各页面各自处理错误提示，风格不统一且可能遗漏。
- 目标:
  - 实现 `src/components/common/ToastNotification.vue` 组件
  - 在 `api.ts` 中统一拦截非 2xx 响应，触发全局 toast
  - 支持 info / success / warning / error 四种类型
  - 支持自动消失和手动关闭
  - 各页面保留关键业务错误的本地处理，其余走全局通知
- 涉及文件: `frontend/src/services/api.ts`、`frontend/src/components/common/ToastNotification.vue`

### D-3. 数据加载骨架屏

- 严重程度: 低
- 现状: 管理后台加载反馈队列、用户页面加载已提交 Issue 列表时，白屏跳跃后直接出现数据。
- 目标:
  - 为 `FeedbackQueue`、`SubmittedHistory`、`DraftEditor` 分别实现 `SkeletonLoader` 占位动画
  - 用 `Suspense` + `async setup` 或 `v-if` 切换骨架/内容状态
- 涉及文件: `frontend/src/components/admin/`、`frontend/src/components/public/`

---

## E. 上手性与工程化

### E-1. 添加 Docker Compose 一键启动

- 严重程度: 高
- 现状:
  - 无 `Dockerfile`、无 `docker-compose.yml`
  - 前后端需分两个终端手动启动，新开发者上手成本高
  - 无 CI/CD 流水线（无 `.github/workflows/`）
- 目标:
  - 编写 `backend/Dockerfile`（基于 `python:3.12-slim`，安装依赖并启动 uvicorn）
  - 编写 `frontend/Dockerfile`（基于 `node:22-alpine`，安装依赖并启动 Vite dev server）
  - 编写根目录 `docker-compose.yml`，编排前后端服务、端口映射、volume 挂载
  - `.env` 文件通过 `env_file` 或 `environment` 注入
- 验证: `docker compose up` 后本地可访问 `http://localhost:5173`，API 可代理到后端。

### E-2. 单个快速启动脚本

- 严重程度: 中
- 现状: 无 `start.sh` 或等效脚本。
- 目标: 编写根目录 `start.sh`，后台启动后端、前台启动前端，Ctrl+C 时同时终止两个进程。
  ```bash
  #!/bin/bash
  cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
  BACKEND=$!
  cd ../frontend && npm run dev &
  FRONTEND=$!
  trap "kill $BACKEND $FRONTEND" EXIT
  wait
  ```

### E-3. 引入代码风格工具

- 严重程度: 低
- 现状: 无 ESLint、Prettier、Black、Ruff 等配置。
- 目标:
  - 前端: 安装 `eslint` + `@eslint/js` + `eslint-plugin-vue`，配置 `eslint.config.js`
  - 前端: 安装 `prettier`，配置 `.prettierrc`
  - 后端: 安装 `ruff`，配置 `pyproject.toml` 或 `ruff.toml`
  - 在 `package.json` / `Makefile` 中补充 `lint` 和 `format` 脚本
- 注意: 首次运行可能产生大量 lint 错误，建议分文件逐步修复。

### E-4. Python 依赖锁定

- 严重程度: 低
- 现状:
  - `requirements.txt` 仅列出 `fastapi==0.116.1` 和 `uvicorn==0.35.0`
  - `pydantic` 由 FastAPI 自动引入但未显式声明
  - 无锁文件，CI 中版本可能漂移
- 目标:
  - 补齐 `requirements.txt` 中所有直接依赖（`pydantic`、`bcrypt`、`httpx` 等）
  - 生成 `requirements.lock`（通过 `pip freeze` 或 `pip-tools` 的 `pip-compile`）

### E-5. CI/CD 流水线

- 严重程度: 中
- 目标:
  - 编写 `.github/workflows/ci.yml`
  - 触发条件: `push` 到 `main` 和 PR 到 `main`
  - 步骤: checkout -> 安装 Python 依赖 -> 后端单元测试 + E2E -> 安装 Node 依赖 -> 前端测试 + 构建
- 参考结构:
  ```yaml
  name: CI
  on: [push, pull_request]
  jobs:
    backend:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-python@v5
          with: { python-version: '3.12' }
        - run: pip install -r backend/requirements.txt
        - run: cd backend && python -m unittest discover -s tests
        - run: cd backend && python tests/e2e_public_feedback_guardrails.py
        - run: cd backend && python tests/e2e_admin_session_flow.py
    frontend:
      runs-on: ubuntu-latest
      steps:
        - uses: actions/checkout@v4
        - uses: actions/setup-node@v4
          with: { node-version: '22' }
        - run: cd frontend && npm ci
        - run: cd frontend && npm test
        - run: cd frontend && npm run build
  ```

---

## F. 前端 UI/UX

### F-1. 响应式布局验证与修复

- 严重程度: 中
- 现状: 未发现 `@media` 查询或移动端适配规则，管理后台三栏布局和公开提交页在窄屏下可能塌陷或溢出。
- 目标:
  - 审查 `components.css`、`layout.css` 中的所有固定宽度/高度（如 `width: 800px`、`min-width: 1200px`）
  - 对管理后台三栏布局添加移动端折叠逻辑：窄屏时三栏变为纵向堆叠，通过 tab 切换队列/审阅/草稿
  - 对公开提交页表单在小屏幕下保证按钮和输入框全宽、垂直间距合理
  - 添加移动端断点: `@media (max-width: 768px)` 和 `@media (max-width: 480px)`

### F-2. 暗色模式支持

- 严重程度: 低
- 现状: 仅有浅色主题，CSS 变量已定义但无暗色变量集合。
- 目标:
  - 在 `tokens.css` 中新增 `[data-theme="dark"]` 选择器的暗色变量集合
  - 在 `base.css` 或 `App.vue` 中添加 `prefers-color-scheme: dark` 媒体查询自动切换
  - 可选：添加手动切换按钮（localStorage 持久化偏好）
  - 前端组件测试验证根元素上 `data-theme` 属性的正确设置

---

## G. 优先级排序建议

推荐推进顺序（前 5 项为核心安全与质量基线）：

| 顺序 | 编号 | 类别 | 预估工作量 |
|------|------|------|-----------|
| 1 | A-1 | 密码哈希迁移 bcrypt | 小 |
| 2 | B-1 | config.py 测试补齐 | 中 |
| 3 | A-2 | auth.py 单元测试 | 中 |
| 4 | C-1 | AdminWorkbenchPage 拆分 | 大 |
| 5 | C-2 | CSS 模块化拆分 | 中 |
| 6 | E-1 | Docker Compose | 中 |
| 7 | F-1 | 响应式适配 | 中 |
| 8 | D-1 | 404 页面 | 小 |
| 9 | C-3 | UserHomePage 拆分 | 中 |
| 10 | D-2 | Toast 通知组件 | 中 |
| 11 | B-2 | main.py 测试 | 中 |
| 12 | E-5 | CI/CD 流水线 | 中 |
| 13 | E-2 | 快速启动脚本 | 小 |
| 14 | F-2 | 暗色模式 | 小 |
| 15 | D-3 | 骨架屏 | 小 |
| 16 | E-3 | 代码风格工具 | 中 |
| 17 | E-4 | Python 依赖锁定 | 小 |
| 18 | B-3 | responses.py 测试 | 小 |
| 19 | B-4 | 前端引导测试 | 小 |

---

## H. 验证清单

每完成一项，确认以下验证通过：

- [ ] 新增/修改的测试全部通过（`npm test` / `python -m unittest`）
- [ ] 前端构建成功（`npm run build`）
- [ ] 后端 E2E 4 条全部通过
- [ ] `git diff --check` 无空白警告
- [ ] 不引入新的 `console.log`、注释掉的代码或调试输出
- [ ] `.env` 和 `.db` 文件不在暂存区
