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
uvicorn app.main:app --reload --host 0.0.0.0 --port 3001

# Run backend tests from /workspace/backend
python3 -m unittest discover -s tests
```

### Backend environment variables

```bash
GITHUB_TOKEN=<server-side-token>
GITHUB_REPO_OWNER=<repo-owner>
GITHUB_REPO_NAME=<repo-name>
AI_API_KEY=<optional>
AI_API_BASE_URL=<optional>
AI_MODEL=<optional>
DATABASE_URL=sqlite:////workspace/backend/data/issue_aggregator.db
API_BASE_PATH=/api
ADMIN_API_NAMESPACE=workbench
ADMIN_API_TOKEN=<admin-token>
ENABLE_API_DOCS=false
RATE_LIMIT_PER_HOUR=20
RELATED_ID_RATE_LIMIT_WINDOW=24
```

说明：

- 管理接口默认收口到 `/api/admin/workbench/*`
- `ADMIN_API_NAMESPACE` 用于管理路由分组与隔离前后台路径
- 管理接口要求请求头 `X-Admin-Token` 与 `ADMIN_API_TOKEN` 匹配
- 生产部署仍建议通过网关或反向代理限制 `/api/admin/*` 的访问入口
- 生产环境默认关闭 FastAPI 文档页，只有在 `ENABLE_API_DOCS=true` 时才暴露 `/docs`
- 配置 `AI_API_KEY`、`AI_API_BASE_URL` 和 `AI_MODEL` 后，草稿生成会调用 OpenAI-compatible Chat Completions 接口
- 未完整配置 AI 参数时，草稿生成使用内置确定性模板

MiMo Token Plan 示例：

```bash
AI_API_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
AI_MODEL=mimo-v2.5-pro
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
VITE_ADMIN_API_NAMESPACE=workbench
VITE_ADMIN_API_TOKEN=<optional-admin-token-for-trusted-preview>
```

说明：

- `VITE_API_BASE_PATH` 需要与后端 `API_BASE_PATH` 保持一致
- `VITE_ADMIN_API_NAMESPACE` 需要与后端 `ADMIN_API_NAMESPACE` 保持一致
- 本地开发时，Vite 代理会按 `VITE_API_BASE_PATH` 转发到 `http://localhost:3001`
- 管理请求会自动读取 `VITE_ADMIN_API_TOKEN` 或 `sessionStorage.issueAggregatorAdminToken` 并发送 `X-Admin-Token`
- `VITE_ADMIN_API_TOKEN` 会进入前端构建产物，只适合受控预览环境

### Admin workbench flow

管理员工作台入口为 `/admin`，当前交互按三栏工作流组织：

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

当前交付包为 `frontend/issue-aggregator-frontend-dist-cohesive-ui.zip`。将 `frontend/dist/` 压缩为 zip 后，可直接上传到静态托管目录；运行期需要将 `VITE_API_BASE_PATH` 对应的路径前缀反向代理到后端服务。

### Current implementation status

- Backend health check endpoint is available at `/api/health`
- SQLite schema initialization runs on startup
- Frontend routes `/` and `/admin` are fully wired to the MVP workflow
- Vite proxy forwards the configured `VITE_API_BASE_PATH` to `http://localhost:3001`
- Admin API endpoints are namespaced under `/api/admin/<ADMIN_API_NAMESPACE>`
- Admin API endpoints require `X-Admin-Token`
- Backend adds stronger payload length limits, duplicate ID validation, resource ID format validation, and security headers
- Admin flow supports batch creation, draft generation, draft editing, and GitHub submission
- Admin workbench now uses inbox queue, review decision board, and draft editor panel as the primary operating model
- Frontend component tests cover user page and admin page core interactions
