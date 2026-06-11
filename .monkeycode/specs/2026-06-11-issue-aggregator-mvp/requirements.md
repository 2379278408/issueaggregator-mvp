# Requirements Document

## Introduction

本功能用于把开源社区中零散、口语化的用户反馈汇总为可审核、可编辑、可提交的 GitHub Issue 草稿，并在前端展示已提交 Issue 列表，帮助后续用户避免重复反馈。

MVP 范围聚焦单仓库、单管理员、单次人工审核提交流程。系统目标是提升反馈整理效率、提高 Issue 质量、保留人工把关能力，并确保对外提交行为可追踪。

## Glossary

- **System**: 开源社区 Issue 聚合反馈系统。
- **Feedback Item**: 用户提交的一条原始反馈。
- **Draft Batch**: 一次人工勾选后进入整合流程的一组反馈。
- **Draft**: AI 基于一个 Draft Batch 生成的 Issue 草稿。
- **Administrator**: 在后台管理反馈、生成草稿并执行提交的人员。
- **Submission**: 管理员确认后发送到 GitHub 的一次 Issue 创建动作。
- **Related ID**: 由用户输入的业务关联标识，用于标识同一功能点、同一问题域或同一需求主题。

## Requirements

### Requirement 1

**User Story:** AS a community user, I want to submit raw feedback quickly, so that I can report problems or suggestions with low friction.

#### Acceptance Criteria

1. WHEN a user submits a feedback form, the System SHALL store one Feedback Item with the submitted raw content, feedback type, and related identifier.
2. WHEN the System stores a new Feedback Item, the System SHALL assign the Feedback Item status as `pending`.
3. IF a user submits an empty feedback body, the System SHALL reject the submission and present a validation message.
4. IF a user submits a feedback form without a related identifier, the System SHALL reject the submission and present a validation message.
5. WHEN a user submits a related identifier, the System SHALL validate the related identifier format against the system rule.
6. WHEN a user submits a feedback form successfully, the System SHALL present a success message.

### Requirement 2

**User Story:** AS a community user, I want to view recently submitted issues before I submit feedback, so that I can decide whether the problem or request already exists.

#### Acceptance Criteria

1. WHEN a user opens the feedback page, the System SHALL display a list of submitted GitHub Issues.
2. WHEN the System displays submitted GitHub Issues, the System SHALL include the issue title, issue number, issue URL, related identifier, and submission time.
3. WHEN a user inspects the submitted GitHub Issue list, the System SHALL allow the user to open the GitHub Issue URL.
4. WHEN the System displays submitted GitHub Issues, the System SHALL sort the list by submission time in descending order.
5. WHEN a user searches the submitted GitHub Issue list, the System SHALL allow filtering by related identifier, feedback type, and keyword.
6. WHEN a user enters a related identifier that already exists in submitted GitHub Issues, the System SHALL display a duplicate warning and the matched GitHub Issue entries.

### Requirement 3

**User Story:** AS an Administrator, I want to browse and select pending feedback items, so that I can decide which items belong in the same issue draft.

#### Acceptance Criteria

1. WHEN an Administrator opens the management list, the System SHALL display Feedback Items with status, type, creation time, and raw content summary.
2. WHEN an Administrator selects multiple Feedback Items, the System SHALL allow the Administrator to create one Draft Batch from the selected Feedback Items.
3. IF a Feedback Item already belongs to an active Draft Batch, the System SHALL display the existing association.
4. WHEN a Draft Batch is created, the System SHALL record the selected Feedback Item identifiers in that Draft Batch.
5. WHEN an Administrator creates a Draft Batch, the System SHALL display the related identifiers included in the selected Feedback Items.
6. IF selected Feedback Items contain multiple related identifiers, the System SHALL require explicit Administrator confirmation before batch creation.

### Requirement 4

**User Story:** AS an Administrator, I want the System to generate one structured issue draft from a selected batch, so that I can reduce manual drafting time.

#### Acceptance Criteria

1. WHEN an Administrator triggers draft generation for one Draft Batch, the System SHALL send the batch feedback content to the AI service.
2. WHEN the AI service returns a result, the System SHALL store one Draft linked to the Draft Batch.
3. WHEN the System stores a Draft, the System SHALL include a title and Markdown body in the Draft.
4. IF the AI service cannot produce a complete section, the System SHALL preserve the missing section with an explicit placeholder.
5. IF the AI service request fails, the System SHALL record the failure status and error summary for the Draft Batch.
6. WHEN the System generates a Draft, the System SHALL include the related identifier summary for the Draft Batch.
7. WHEN the System generates a Draft, the System SHALL structure the Draft body with a fixed issue template.

### Requirement 5

**User Story:** AS an Administrator, I want to review and edit the generated draft, so that I can ensure the final GitHub issue is accurate and professional.

#### Acceptance Criteria

1. WHEN an Administrator opens a generated Draft, the System SHALL display the Draft content and the linked raw Feedback Items together.
2. WHEN an Administrator edits the Draft title or body, the System SHALL save the latest Draft content.
3. WHILE a Draft is awaiting final confirmation, the System SHALL keep the Draft status as `draft_ready`.
4. WHEN an Administrator confirms the Draft for submission, the System SHALL change the Draft status to `approved`.
5. WHEN an Administrator reviews a Draft, the System SHALL display related submitted GitHub Issues with the same related identifier.

### Requirement 6

**User Story:** AS an Administrator, I want to submit an approved draft to GitHub once, so that the repository receives one clean issue instead of many fragmented reports.

#### Acceptance Criteria

1. WHEN an Administrator submits an approved Draft, the System SHALL create one GitHub Issue through the GitHub API.
2. WHEN GitHub returns success, the System SHALL store the GitHub issue number, issue URL, and related identifier.
3. WHEN a Draft submission succeeds, the System SHALL set the Draft Batch status to `submitted`.
4. WHEN a Draft submission succeeds, the System SHALL set each linked Feedback Item status to `submitted`.
5. IF the GitHub API request fails, the System SHALL retain the Draft content and record the failure summary.
6. WHEN the System submits a Draft to GitHub, the System SHALL include the related identifier in the submitted issue body.

### Requirement 7

**User Story:** AS a project owner, I want the submission workflow to remain reviewable and secure, so that the system can operate safely in a real repository environment.

#### Acceptance Criteria

1. WHEN the System calls the GitHub API, the System SHALL use a server-side access token stored outside the frontend.
2. WHEN an Administrator submits Drafts, the System SHALL require an explicit manual action for each submission.
3. WHEN the System receives repeated submission attempts, the System SHALL enforce a configurable rate limit.
4. WHEN the System records draft generation or submission events, the System SHALL preserve timestamps and operation results for later review.
5. WHEN the System receives repeated submissions for the same related identifier within the configured time window, the System SHALL enforce a related-identifier rate limit.

## Related Identifier Rule

- `related_id` 表示一个稳定的问题域或功能主题。
- `related_id` 推荐格式为小写字母、数字和短横线组成的 slug。
- 示例：`editor-copy-button`、`login-oauth-flow`、`settings-sync-error`。
- 相同主题的反馈应复用同一个 `related_id`。
- 新主题应创建新的 `related_id`。

## GitHub Issue Template

每条提交到 GitHub 的 Issue 应包含以下固定结构：

- `Summary`
- `Related ID`
- `User Signals Count`
- `Background`
- `Steps to Reproduce`
- `Expected Behavior`
- `Actual Behavior`
- `Impact`
- `Missing Information`

## MVP Scope

- 单 GitHub 仓库。
- 单管理员后台。
- 用户端仅支持文本反馈提交。
- 用户端展示最近已提交的 Issue 列表。
- 用户提交时必须填写 `related_id`。
- 用户端支持按 `related_id`、类型、关键词搜索已提交 Issue。
- 用户端对重复 `related_id` 提供明确提示。
- 管理员手动勾选反馈组成批次。
- 管理员创建批次时可见 `related_id` 分布。
- 每个批次生成一条 Draft。
- 每条 Draft 需要人工审核后才能提交。

## Out of Scope

- 多仓库分发。
- 自动提交 Issue。
- 自动标签分配。
- Issue 评论同步与更新。
- 多管理员协同权限系统。
