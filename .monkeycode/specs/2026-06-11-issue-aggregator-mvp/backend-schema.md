# Backend Schema Draft

## Overview

本文件定义后端 SQLite 的初版表结构草稿，用于指导迁移、Repository 和 API 返回结构实现。

## Tables

### 1. `feedback_items`

字段：

- `id` TEXT PRIMARY KEY
- `type` TEXT NOT NULL
- `related_id` TEXT NOT NULL
- `expected_behavior` TEXT NULL
- `actual_behavior` TEXT NULL
- `raw_content` TEXT NOT NULL
- `status` TEXT NOT NULL
- `created_at` TEXT NOT NULL
- `submitted_at` TEXT NULL

建议索引：

- `idx_feedback_items_status`
- `idx_feedback_items_related_id`
- `idx_feedback_items_created_at`

### 2. `draft_batches`

字段：

- `id` TEXT PRIMARY KEY
- `status` TEXT NOT NULL
- `primary_related_id` TEXT NULL
- `related_id_count` INTEGER NOT NULL DEFAULT 0
- `integration_error` TEXT NULL
- `created_at` TEXT NOT NULL
- `updated_at` TEXT NOT NULL

建议索引：

- `idx_draft_batches_status`
- `idx_draft_batches_primary_related_id`

### 3. `draft_batch_items`

字段：

- `id` TEXT PRIMARY KEY
- `batch_id` TEXT NOT NULL
- `feedback_item_id` TEXT NOT NULL

约束：

- `UNIQUE(feedback_item_id)` 用于限制未迁移策略下的唯一归属

### 4. `drafts`

字段：

- `id` TEXT PRIMARY KEY
- `batch_id` TEXT NOT NULL
- `title` TEXT NOT NULL
- `body_markdown` TEXT NOT NULL
- `related_id_summary` TEXT NOT NULL
- `status` TEXT NOT NULL
- `ai_model` TEXT NULL
- `prompt_snapshot` TEXT NULL
- `updated_at` TEXT NOT NULL

建议索引：

- `idx_drafts_batch_id`
- `idx_drafts_status`

### 5. `submissions`

字段：

- `id` TEXT PRIMARY KEY
- `draft_id` TEXT NOT NULL
- `github_issue_number` INTEGER NOT NULL
- `github_issue_url` TEXT NOT NULL
- `related_id` TEXT NOT NULL
- `github_state` TEXT NULL
- `labels_snapshot` TEXT NULL
- `response_status` INTEGER NOT NULL
- `submitted_at` TEXT NOT NULL
- `error_summary` TEXT NULL

建议索引：

- `idx_submissions_related_id`
- `idx_submissions_submitted_at`
- `idx_submissions_github_issue_number`

## Enum Suggestions

### `feedback_items.status`

- `pending`
- `grouped`
- `submitted`

### `draft_batches.status`

- `created`
- `integrating`
- `draft_ready`
- `approved`
- `submitted`
- `failed`

### `drafts.status`

- `draft_ready`
- `approved`
- `submitted`
- `failed`

## Related ID Validation Rule

推荐正则：

```text
^[a-z0-9]+(?:-[a-z0-9]+)*$
```

## Notes for Implementation

- 所有时间字段统一存 ISO 8601 UTC。
- 后续如果要保留一条反馈进入多个历史批次，需要把 `draft_batch_items` 的唯一约束改为“仅限制活跃批次”。
- `submissions` 是前端历史 Issue 列表的直接数据来源。
