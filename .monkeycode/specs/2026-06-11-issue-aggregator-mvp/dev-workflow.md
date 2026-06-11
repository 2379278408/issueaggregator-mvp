# Development Workflow

## Goal

本文件用于统一后续连续开发时的顺序、联调方式、测试切入点和预览策略。

## Development Order

### Stage 1: Backend skeleton

- 建立 FastAPI 项目结构
- 建立 SQLite schema 和初始化逻辑
- 建立基础 Repository 和 service 层
- 提供健康检查接口和基础错误处理

### Stage 2: Feedback flow

- 实现 `POST /api/feedback`
- 实现 `GET /api/issues/submitted`
- 实现 `GET /api/issues/submitted/search`
- 实现 `GET /api/feedback`

### Stage 3: Draft workflow

- 实现 `POST /api/draft-batches`
- 实现 `POST /api/draft-batches/{id}/integrate`
- 实现 `GET /api/drafts/{id}`
- 实现 `PUT /api/drafts/{id}`

### Stage 4: GitHub submission flow

- 实现 `POST /api/drafts/{id}/submit`
- 实现 GitHub API client
- 实现提交结果回写和状态联动

### Stage 5: Vue frontend

- 初始化 Vue + Vite 工程
- 配置 `/api` 代理
- 实现用户页
- 实现后台页
- 接入真实接口

## Preview Strategy

预览阶段使用以下方式：

- 前端通过 Vite dev server 暴露
- 后端通过本地端口运行
- 前端使用 `/api` 反向代理联调后端

满足可以跑起来的条件后，立即启动预览。

## Manual Verification Checklist

### User page

- 历史 Issue 列表可见
- 搜索和筛选可用
- 输入重复 `related_id` 时出现提示
- 表单校验工作正常
- 反馈提交成功提示正常

### Admin page

- 待处理反馈表格可见
- 选中反馈后批次摘要正确
- 混合 `related_id` 出现确认提示
- Draft 能生成、查看、编辑
- 提交后能看到 Issue 编号和链接

## Deployment Readiness Checklist

- 后端配置环境变量读取 GitHub Token 和 AI Key
- 前端构建成功生成 `dist/`
- 前端构建产物通过 zip 可上传
- 服务器静态目录路径已知
- 服务器上的 `/api` 指向后端服务

## Suggested Environment Variables

- `GITHUB_TOKEN`
- `GITHUB_REPO_OWNER`
- `GITHUB_REPO_NAME`
- `AI_API_KEY`
- `AI_API_BASE_URL`
- `DATABASE_URL`
- `RATE_LIMIT_PER_HOUR`
- `RELATED_ID_RATE_LIMIT_WINDOW`
