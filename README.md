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
DATABASE_URL=sqlite:////workspace/backend/data/issue_aggregator.db
RATE_LIMIT_PER_HOUR=20
RELATED_ID_RATE_LIMIT_WINDOW=24
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

### Deployment artifact

前端部署产物目录为 `frontend/dist/`。

标准交付流程：

```bash
# Build production assets
cd /workspace/frontend && npm run build

# Optional: verify tests before packaging
cd /workspace/frontend && npm test
```

将 `frontend/dist/` 压缩为 zip 后，可直接上传到静态托管目录；运行期 `/api` 继续反向代理到后端服务。

### Current implementation status

- Backend health check endpoint is available at `/api/health`
- SQLite schema initialization runs on startup
- Frontend routes `/` and `/admin` are fully wired to the MVP workflow
- Vite proxy forwards `/api` to `http://localhost:3001`
- Admin flow supports batch creation, draft generation, draft editing, and GitHub submission
- Frontend component tests cover user page and admin page core interactions
