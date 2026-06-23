# Issue Aggregator 接口说明

## 1. 路由入口

前端路由：

- `/`: 公开提交页
- `/<VITE_ADMIN_ROUTE_SLUG>`: 管理工作台，默认 `adminconsole`
- `/:pathMatch(.*)*`: 404 页面

默认 API 前缀：

- 公开接口前缀: `/api`
- 管理接口前缀: `/api/admin/<ADMIN_API_NAMESPACE>`
- 默认管理命名空间: `workbench`

## 2. 响应契约

前后端统一使用 envelope：

成功：

```json
{
  "success": true,
  "data": {}
}
```

失败：

```json
{
  "success": false,
  "data": null,
  "error_code": "ERROR_CODE",
  "message": "错误说明"
}
```

前端 `api.ts` 会把非结构化响应统一归并为 `INVALID_API_RESPONSE`。

## 3. 公开接口

### `GET /api/health`

用途：健康检查。

### `POST /api/feedback`

用途：提交公开反馈。

请求体字段：

- `type`: 反馈类型
- `related_id`: 关联标识
- `raw_content`: 原始描述
- `expected_behavior`: 可选
- `actual_behavior`: 可选
- `page_url`: 可选

服务端处理要点：

- 校验来源 `Origin`
- 校验 `related_id` 规则
- 拦截重复窗口内的重复提交
- 统计公开反馈 IP 日限流

### `GET /api/issues/submitted`

用途：列出已提交 GitHub Issue。

### `GET /api/issues/submitted/search`

用途：按 `related_id`、`keyword`、`type` 查询已提交 Issue。

## 4. 管理会话接口

### `POST /api/admin/workbench/session/login`

用途：管理员登录。

请求体字段：

- `username`
- `password`

成功后返回：

- `username`
- `session_expires_at`
- `idle_expires_at`

同时由后端写入 `HttpOnly` session cookie。

### `GET /api/admin/workbench/session/me`

用途：查询当前会话状态。

返回字段：

- `authenticated`
- `username`
- `session_expires_at`
- `idle_expires_at`

### `POST /api/admin/workbench/session/logout`

用途：登出并失效当前会话。

## 5. 管理业务接口

### `GET /api/admin/workbench/feedback`

用途：按状态拉取反馈队列。

常见状态：

- `pending`
- `grouped`
- `submitted`

### `GET /api/admin/workbench/audit-events`

用途：查询审计事件。

支持筛选：

- 事件类型
- 时间范围
- 关键词

### `POST /api/admin/workbench/draft-batches`

用途：创建反馈批次。

请求体字段：

- `feedback_item_ids`: 反馈 ID 列表
- `confirm_mixed_related_ids`: 是否确认跨 `related_id` 混批

### `POST /api/admin/workbench/draft-batches/{batch_id}/integrate`

用途：整合批次并生成草稿。

### `GET /api/admin/workbench/drafts/{draft_id}`

用途：读取草稿。

### `PUT /api/admin/workbench/drafts/{draft_id}`

用途：更新草稿标题和正文。

请求体字段：

- `title`
- `body_markdown`

### `POST /api/admin/workbench/drafts/{draft_id}/submit`

用途：把草稿提交到 GitHub Issue。

成功返回：

- `draft_id`
- `issue_number`
- `issue_url`
- `related_id`
- `submitted_at`

## 6. 前端环境变量

- `VITE_API_BASE_PATH`: 默认 `/api`
- `VITE_API_PROXY_TARGET`: 默认 `http://localhost:8000`
- `VITE_ADMIN_API_NAMESPACE`: 默认 `workbench`
- `VITE_ADMIN_ROUTE_SLUG`: 默认 `adminconsole`

## 7. 后端关键环境变量

- `APP_ENV`
- `DATABASE_URL`
- `API_BASE_PATH`
- `ADMIN_API_NAMESPACE`
- `ADMIN_ROUTE_SLUG`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD_HASH`
- `ADMIN_SESSION_COOKIE_NAME`
- `ENABLE_API_DOCS`
- `GITHUB_TOKEN`
- `GITHUB_REPO_OWNER`
- `GITHUB_REPO_NAME`
- `AI_API_KEY`
- `AI_API_BASE_URL`
- `AI_MODEL`
- `PUBLIC_FEEDBACK_ALLOWED_ORIGINS`
- `PUBLIC_FEEDBACK_DAILY_IP_LIMIT`
- `PUBLIC_FEEDBACK_DUPLICATE_WINDOW_MINUTES`
- `TRUST_PROXY_HEADERS`

## 8. 集成注意事项

- 前端管理命名空间必须与后端 `ADMIN_API_NAMESPACE` 保持一致。
- 前端管理路由 slug 必须与后端 `ADMIN_ROUTE_SLUG` 保持一致。
- 生产环境需要为 `/api` 提供统一入口，并保留 session cookie。
- 未配置 AI 参数时，后端使用确定性模板生成草稿。
