# Issue Aggregator MVP

Issue Aggregator 是一个用于整理用户反馈并生成 GitHub Issue 的前后端一体化项目。

当前主链路已经打通：

1. 用户在公开页提交反馈
2. 管理员在工作台聚合反馈并创建批次
3. 系统生成草稿，管理员可继续编辑
4. 草稿提交到 GitHub
5. 审计面板回看认证和关键操作事件

## 项目结构

- `frontend/`: Vue 3 + Vite 前端
- `backend/`: FastAPI + SQLite 后端
- `.monkeycode/docs/`: 项目文档
- `docker-compose.yml`: 本地容器化启动
- `start.sh`: 本地同时启动前后端

## 项目文档

完整文档位于 `.monkeycode/docs/`：

- `INDEX.md`: 文档索引
- `ARCHITECTURE.md`: 系统架构说明
- `INTERFACES.md`: API 和路由契约
- `DEVELOPER_GUIDE.md`: 开发与测试指南
- `RELEASE_CHECKLIST.md`: 最后一次安全推送检查清单

## 本地启动

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

也可以直接在仓库根目录执行 `./start.sh`。

## 常用命令

前端验证：

```bash
npm run lint
npm test
npm run build
```

执行目录：`/workspace/frontend`

后端验证：

```bash
python3 -m unittest discover -s tests
python3 tests/e2e_public_feedback_guardrails.py
python3 tests/e2e_admin_batch_flow.py
python3 tests/e2e_github_submit_flow.py
python3 tests/e2e_admin_session_flow.py
```

执行目录：`/workspace/backend`

## 环境变量

后端常用变量：

- `APP_ENV`
- `DATABASE_URL`
- `API_BASE_PATH`
- `ADMIN_API_NAMESPACE`
- `ADMIN_ROUTE_SLUG`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD_HASH`
- `GITHUB_TOKEN`
- `GITHUB_REPO_OWNER`
- `GITHUB_REPO_NAME`
- `AI_API_KEY`
- `AI_API_BASE_URL`
- `AI_MODEL`

前端常用变量：

- `VITE_API_BASE_PATH`
- `VITE_API_PROXY_TARGET`
- `VITE_ADMIN_API_NAMESPACE`
- `VITE_ADMIN_ROUTE_SLUG`

更完整说明见 `.monkeycode/docs/INTERFACES.md`。
