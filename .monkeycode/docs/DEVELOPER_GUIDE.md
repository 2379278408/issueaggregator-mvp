# Issue Aggregator 开发者指南

## 1. 环境要求

- Python 3.12
- Node.js 22
- npm
- SQLite 通过 Python 标准库驱动使用，无需单独安装

## 2. 本地启动

### 方式一：分别启动

后端：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

执行目录：`/workspace/backend`

前端：

```bash
npm run dev -- --host 0.0.0.0 --port 5173
```

执行目录：`/workspace/frontend`

### 方式二：统一脚本

根目录提供 `start.sh`，会同时拉起前后端。

## 3. Docker Compose

根目录提供 `docker-compose.yml`，包含：

- `backend`: 从 `backend/Dockerfile` 构建，暴露 `8000`
- `frontend`: 从 `frontend/Dockerfile` 构建，暴露 `5173`

注意事项：

- `backend/.env` 和 `frontend/.env` 会作为运行时环境注入
- 前端依赖后端服务
- 前端开发代理已在 `vite.config.ts` 中配置

## 4. 测试命令

前端：

```bash
npm run lint
npm test
npm run build
```

执行目录：`/workspace/frontend`

后端：

```bash
python3 -m unittest discover -s tests
python3 tests/e2e_public_feedback_guardrails.py
python3 tests/e2e_admin_batch_flow.py
python3 tests/e2e_github_submit_flow.py
python3 tests/e2e_admin_session_flow.py
```

执行目录：`/workspace/backend`

补充说明：

- 若使用 `pytest` 跑定向后端测试，需要显式设置 `PYTHONPATH=/workspace/backend`
- 浏览器级 E2E 命令位于 `frontend/package.json`

## 5. 浏览器级 E2E

后台验收：

```bash
ADMIN_E2E_URL=<后台预览地址> ADMIN_E2E_USERNAME=<用户名> ADMIN_E2E_PASSWORD=<密码> npm run e2e:admin
```

全链路验收：

```bash
PIPELINE_E2E_URL=<API地址> PIPELINE_E2E_ADMIN_ROUTE=<路由slug> npm run e2e:pipeline
```

可选真实提交：

- `ADMIN_E2E_SUBMIT=true`
- `PIPELINE_E2E_SUBMIT=true`

## 6. CI 状态

GitHub Actions 工作流位于 `.github/workflows/ci.yml`。

当前 CI 包含两部分：

- `backend`: 安装依赖、执行单测、执行 4 条后端 E2E
- `frontend`: 安装依赖、执行组件测试、执行构建

## 7. 开发约定

- 所有回复和界面文案优先使用简体中文。
- 管理接口默认收口到 `/api/admin/<namespace>`。
- 前端开发服务必须通过反向代理访问后端 API。
- 提交前执行测试和构建验证。
- 开发态数据库默认使用 `backend/data/issue_aggregator.dev.db`，避免污染已跟踪运行库。

## 8. 常见问题

### 管理页返回登录态

优先检查：

- `ADMIN_USERNAME`
- `ADMIN_PASSWORD_HASH`
- `ADMIN_SESSION_COOKIE_NAME`
- 前后端的 `ADMIN_API_NAMESPACE` 是否一致

### 前端看不到数据

优先检查：

- 后端是否已监听 `8000`
- `VITE_API_PROXY_TARGET` 是否仍指向 `http://localhost:8000`

### 公开反馈被拒绝

优先检查：

- 当前 `Origin` 是否在允许范围内
- 是否触发每日 IP 限流
- 是否命中重复窗口限制

### 审计面板为空

优先检查：

- 管理接口请求是否成功
- `audit_events` 表是否已有事件
