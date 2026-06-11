# API Contract

## Overview

本文件定义 Issue Aggregator MVP 的前后端接口契约，供前端、后端、联调和部署阶段统一使用。

## Base Rule

- 所有接口前缀为 `/api`
- 请求体和响应体均使用 JSON
- 时间字段统一使用 ISO 8601 字符串
- 错误响应统一包含 `error_code`、`message`

## Common Response Shape

成功响应：

```json
{
  "success": true,
  "data": {}
}
```

失败响应：

```json
{
  "success": false,
  "error_code": "VALIDATION_ERROR",
  "message": "related_id 格式无效"
}
```

## 1. Submit Feedback

### `POST /api/feedback`

说明：创建一条用户反馈。

请求体：

```json
{
  "type": "bug",
  "related_id": "editor-copy-button",
  "raw_content": "复制按钮在暗色模式下不可见",
  "expected_behavior": "按钮在暗色模式下可见",
  "actual_behavior": "按钮和背景颜色接近"
}
```

成功响应：

```json
{
  "success": true,
  "data": {
    "id": "fb_001",
    "status": "pending",
    "created_at": "2026-06-11T10:00:00Z"
  }
}
```

## 2. List Submitted Issues

### `GET /api/issues/submitted`

说明：获取已提交到 GitHub 的 Issue 列表，默认按提交时间倒序。

查询参数：

- `page`
- `page_size`

成功响应：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "issue_number": 101,
        "title": "[Bug] Copy button invisible in dark mode",
        "issue_url": "https://github.com/org/repo/issues/101",
        "related_id": "editor-copy-button",
        "type": "bug",
        "submitted_at": "2026-06-11T10:30:00Z"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

## 3. Search Submitted Issues

### `GET /api/issues/submitted/search`

说明：按 `related_id`、类型、关键词搜索已提交 Issue。

查询参数：

- `related_id`
- `type`
- `keyword`

成功响应与列表接口一致。

## 4. List Pending Feedback

### `GET /api/feedback`

说明：管理员获取反馈列表。

查询参数：

- `status`
- `page`
- `page_size`

成功响应：

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": "fb_001",
        "type": "bug",
        "related_id": "editor-copy-button",
        "raw_content": "复制按钮在暗色模式下不可见",
        "status": "pending",
        "created_at": "2026-06-11T10:00:00Z"
      }
    ],
    "page": 1,
    "page_size": 20,
    "total": 1
  }
}
```

## 5. Create Draft Batch

### `POST /api/draft-batches`

说明：管理员勾选反馈后创建批次。

请求体：

```json
{
  "feedback_item_ids": ["fb_001", "fb_002"],
  "confirm_mixed_related_ids": false
}
```

成功响应：

```json
{
  "success": true,
  "data": {
    "id": "batch_001",
    "status": "created",
    "primary_related_id": "editor-copy-button",
    "related_id_count": 1,
    "created_at": "2026-06-11T11:00:00Z"
  }
}
```

## 6. Integrate Draft Batch

### `POST /api/draft-batches/{id}/integrate`

说明：触发 AI 生成 Draft。

成功响应：

```json
{
  "success": true,
  "data": {
    "batch_id": "batch_001",
    "draft_id": "draft_001",
    "status": "draft_ready"
  }
}
```

## 7. Get Draft

### `GET /api/drafts/{id}`

成功响应：

```json
{
  "success": true,
  "data": {
    "id": "draft_001",
    "batch_id": "batch_001",
    "title": "[Bug] Copy button invisible in dark mode",
    "body_markdown": "...",
    "related_id_summary": "editor-copy-button",
    "status": "draft_ready",
    "updated_at": "2026-06-11T11:10:00Z"
  }
}
```

## 8. Update Draft

### `PUT /api/drafts/{id}`

请求体：

```json
{
  "title": "[Bug] Copy button invisible in dark mode",
  "body_markdown": "..."
}
```

成功响应：

```json
{
  "success": true,
  "data": {
    "id": "draft_001",
    "status": "draft_ready",
    "updated_at": "2026-06-11T11:15:00Z"
  }
}
```

## 9. Submit Draft

### `POST /api/drafts/{id}/submit`

说明：管理员确认后提交到 GitHub。

成功响应：

```json
{
  "success": true,
  "data": {
    "draft_id": "draft_001",
    "issue_number": 101,
    "issue_url": "https://github.com/org/repo/issues/101",
    "related_id": "editor-copy-button",
    "submitted_at": "2026-06-11T11:20:00Z"
  }
}
```

## 10. Suggested Error Codes

- `VALIDATION_ERROR`
- `RELATED_ID_FORMAT_INVALID`
- `RELATED_ID_RATE_LIMITED`
- `FEEDBACK_ALREADY_GROUPED`
- `DRAFT_BATCH_EMPTY`
- `MIXED_RELATED_ID_CONFIRM_REQUIRED`
- `AI_INTEGRATION_FAILED`
- `GITHUB_SUBMIT_FAILED`
- `TOKEN_MISSING`
- `INTERNAL_ERROR`
