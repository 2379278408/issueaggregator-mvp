# Three-Layer Memory

This repository initializes a minimal three-layer memory mechanism under `.monkeycode/memory/`.

## Layers

- `L0`: atomic raw memories
- `L1`: topic summaries
- `L2`: global profile

## Storage rule

The storage policy is `append_only_with_prune`:

- new memory uses `append`
- memory reduction uses `prune`
- in-place mutation is disabled
- hard delete is disabled

## Commands

```bash
# Initialize files
node scripts/memory-cli.js init

# Append a memory event
node scripts/memory-cli.js append L0 "记录一条新的原子记忆"

# Prune a memory event by tombstone
node scripts/memory-cli.js prune L0 bootstrap-l0-001 "该记忆已过时"
```

## Application Workspace

当前代码仓库还包含一个正在开发的 Issue Aggregator MVP：

- `backend/`: FastAPI + SQLite 后端骨架
- `frontend/`: Vue 3 + Vite 前端骨架

### Backend commands

```bash
# Run backend from /workspace/backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run backend tests from /workspace/backend
python3 -m unittest discover -s tests

# Run public feedback guardrail E2E check from /workspace/backend
python3 tests/e2e_public_feedback_guardrails.py
```

### Backend environment variables

```bash
GITHUB_TOKEN=<server-side-token>
GITHUB_REPO_OWNER=<repo-owner>
GITHUB_REPO_NAME=<repo-name>
AI_API_KEY=<optional>
AI_API_BASE_URL=<optional>
AI_MODEL=<optional>
DATABASE_URL=sqlite:////workspace/backend/data/issue_aggregator.dev.db
API_BASE_PATH=/api
ADMIN_API_NAMESPACE=workbench
ADMIN_ROUTE_SLUG=<8-64-char-lowercase-alnum-slug>
ADMIN_USERNAME=<admin-username>
ADMIN_PASSWORD_HASH=<sha256-password-hash>
ADMIN_SESSION_SECRET=<random-session-secret>
ADMIN_SESSION_COOKIE_NAME=ia_admin_session
ADMIN_SESSION_IDLE_MINUTES=120
ADMIN_SESSION_MAX_HOURS=24
ADMIN_LOGIN_FAILURE_LIMIT=5
ADMIN_LOGIN_FAILURE_WINDOW_MINUTES=15
ADMIN_LOGIN_COOLDOWN_MINUTES=30
ADMIN_API_TOKEN=<optional-legacy-token>
ENABLE_API_DOCS=false
RATE_LIMIT_PER_HOUR=20
RELATED_ID_RATE_LIMIT_WINDOW=24
PUBLIC_FEEDBACK_DAILY_IP_LIMIT=5
TRUST_PROXY_HEADERS=false
PUBLIC_FEEDBACK_ALLOWED_ORIGINS=
PUBLIC_FEEDBACK_DUPLICATE_WINDOW_MINUTES=10
```

说明：

- 管理接口默认收口到 `/api/admin/workbench/*`
- `ADMIN_API_NAMESPACE` 用于管理路由分组与隔离前后台路径
- `ADMIN_ROUTE_SLUG` 用于管理后台前端入口路径，默认值为 `adminconsole`
- 管理后台主认证方式为用户名密码登录后写入 `HttpOnly` Session Cookie
- `ADMIN_API_TOKEN` 仍可作为迁移期兼容鉴权方式保留
- 本地开发若显式设置 `DATABASE_URL`，优先指向 `backend/data/issue_aggregator.dev.db` 或其他独立库文件
- 生产部署仍建议通过网关或反向代理限制 `/api/admin/*` 的访问入口
- 生产环境默认关闭 FastAPI 文档页，只有在 `ENABLE_API_DOCS=true` 时才暴露 `/docs`
- 未显式配置 `DATABASE_URL` 时，默认库文件会按 `APP_ENV` 分流：开发态写入 `backend/data/issue_aggregator.dev.db`，演示态写入 `backend/data/issue_aggregator.<env>.db`，生产态写入 `backend/data/issue_aggregator.db`
- 同一 IP 每天最多提交 `PUBLIC_FEEDBACK_DAILY_IP_LIMIT` 次公开反馈
- 默认情况下，服务会直接使用公网来源 IP；当直连来源是私网、回环或链路本地代理地址且请求带有有效 `X-Forwarded-For` 时，会自动改用该 header 的首个 IP 做限流识别
- `TRUST_PROXY_HEADERS=true` 时会无条件优先使用 `X-Forwarded-For`，仅适用于可信反向代理已覆盖该 header 的部署
- 浏览器请求公开反馈接口时，如果带有 `Origin`，默认要求与当前服务同源；配置 `PUBLIC_FEEDBACK_ALLOWED_ORIGINS` 后，会按逗号分隔白名单精确放行
- 公开反馈会在 `PUBLIC_FEEDBACK_DUPLICATE_WINDOW_MINUTES` 窗口内拦截同类型、同关联标识、同正文/期望/实际的重复提交
- 管理接口成功/失败审计事件会写入数据库 `audit_events`，日志中的 `recent_count` 基于最近 10 分钟同类型事件统计
- 管理后台会通过 `GET /api/admin/workbench/audit-events` 展示最近审计事件，便于回看管理员鉴权失败和成功操作
- 配置 `AI_API_KEY`、`AI_API_BASE_URL` 和 `AI_MODEL` 后，草稿生成会调用 OpenAI-compatible Chat Completions 接口
- 未完整配置 AI 参数时，草稿生成使用内置确定性模板

MiMo Token Plan 示例：

```bash
AI_API_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
AI_MODEL=mimo-v2.5
```

### Frontend commands

```bash
# Run frontend from /workspace/frontend
npm run dev -- --host 0.0.0.0 --port 5173

# Build frontend from /workspace/frontend
npm run build

# Run frontend component tests from /workspace/frontend
npm test
```

前端可选环境变量：

```bash
VITE_API_BASE_PATH=/api
VITE_API_PROXY_TARGET=http://localhost:8000
VITE_ADMIN_API_NAMESPACE=workbench
VITE_ADMIN_ROUTE_SLUG=<same-value-as-admin-route-slug>
```

说明：

- `VITE_API_BASE_PATH` 需要与后端 `API_BASE_PATH` 保持一致
- 本地开发时，Vite 代理会按 `VITE_API_BASE_PATH` 转发到 `VITE_API_PROXY_TARGET`，默认值为 `http://localhost:8000`
- `VITE_ADMIN_API_NAMESPACE` 需要与后端 `ADMIN_API_NAMESPACE` 保持一致
- `VITE_ADMIN_ROUTE_SLUG` 需要与后端 `ADMIN_ROUTE_SLUG` 保持一致
- 管理请求会携带浏览器 Session Cookie，并兼容旧 `X-Admin-Token` 迁移路径

### Admin workbench flow

管理员工作台入口为 `/<VITE_ADMIN_ROUTE_SLUG>`，当前交互按三栏工作流组织：

- 左栏：收件箱式反馈队列，支持 `pending`、`grouped`、`submitted` 切换
- 中栏：聚合审阅台，展示建批建议、拆批建议和缺失信息提示
- 右栏：草稿编辑器，展示草稿状态、正文编辑区和 GitHub 提交操作

标准演示路径：

1. 在左栏 `pending` 队列勾选同一主题反馈。
2. 在中栏确认是否建议拆批，以及是否存在缺失信息。
3. 点击“创建批次”进入草稿阶段。
4. 在右栏点击“生成草稿”，再进行人工修订。
5. 保存草稿后点击“提交到 GitHub”。

页面会在关键动作后自动定位到当前步骤：

- 选中反馈后定位到中栏审阅区
- 创建批次后定位到右栏草稿区
- 草稿加载和提交成功后保持在右栏上下文

### Deployment artifact

前端部署产物目录为 `frontend/dist/`。

标准交付流程：

```bash
# Verify component tests
npm test

# Build production assets
npm run build
```

以上命令在 `/workspace/frontend` 下执行。

构建完成后建议检查：

- `frontend/dist/index.html`
- `frontend/dist/assets/*.css`
- `frontend/dist/assets/*.js`

当前交付包为 `frontend/issue-aggregator-frontend-dist-reviewed-fixes-v2.zip`。将 `frontend/dist/` 压缩为 zip 后，可直接上传到静态托管目录；运行期需要将 `VITE_API_BASE_PATH` 对应的路径前缀反向代理到后端服务。

### Troubleshooting

- 管理页回到登录表单：先检查 `ADMIN_USERNAME`、`ADMIN_PASSWORD_HASH`、`ADMIN_SESSION_SECRET` 是否已配置，再确认请求路径是否仍为 `/api/admin/workbench/*`
- 本地前端看不到数据：先确认后端已在 `8000` 端口启动，再检查 `VITE_API_PROXY_TARGET` 是否仍为 `http://localhost:8000`
- 公开反馈提交返回 `403`：先核对浏览器 `Origin` 是否与当前服务同源；跨域预览时把源站加入 `PUBLIC_FEEDBACK_ALLOWED_ORIGINS`
- 公开反馈被快速拦截：检查是否命中 `PUBLIC_FEEDBACK_DAILY_IP_LIMIT`，或是否落在 `PUBLIC_FEEDBACK_DUPLICATE_WINDOW_MINUTES` 窗口内的重复内容规则
- 审计面板为空：先确认管理接口请求成功，再检查数据库 `audit_events` 是否已有 `admin_auth_failed` 或 `admin_action_succeeded` 事件
- 开发时 SQLite 文件持续变脏：优先使用默认开发态库 `backend/data/issue_aggregator.dev.db`，或显式设置独立的 `DATABASE_URL`

### Current implementation status

- Backend health check endpoint is available at `/api/health`
- SQLite schema initialization runs on startup
- Frontend routes `/` and `/<VITE_ADMIN_ROUTE_SLUG>` are fully wired to the MVP workflow
- Vite proxy forwards the configured `VITE_API_BASE_PATH` to `VITE_API_PROXY_TARGET`, defaulting to `http://localhost:8000`
- Admin API endpoints are namespaced under `/api/admin/<ADMIN_API_NAMESPACE>`
- Admin API endpoints accept Session Cookie authentication and keep `X-Admin-Token` as a compatibility path
- Backend adds stronger payload length limits, duplicate ID validation, resource ID format validation, and security headers
- Admin flow supports batch creation, draft generation, draft editing, and GitHub submission
- Admin workbench now uses inbox queue, review decision board, and draft editor panel as the primary operating model
- Frontend component tests cover user page and admin page core interactions
