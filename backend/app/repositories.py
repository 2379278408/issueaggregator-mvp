from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from urllib import error, request
from uuid import uuid4

from .config import get_settings
from .database import connection_context
from .models import (
    AdminLoginAttemptRecord,
    AdminSessionRecord,
    DraftBatchItemRecord,
    DraftBatchRecord,
    DraftBatchStatus,
    DraftRecord,
    DraftStatus,
    DraftUpdatePayload,
    FeedbackCreatePayload,
    FeedbackRecord,
    FeedbackStatus,
    SubmissionRecord,
    new_batch_id,
    new_batch_item_id,
    new_draft_id,
    new_feedback_id,
    new_submission_id,
    utc_now_iso,
)


class RepositoryError(ValueError):
    pass


class AuditEventRepository:
    def create_event(
        self,
        *,
        event_id: str,
        event_type: str,
        client_ip: str,
        path: str,
        action: str | None = None,
        resource_id: str | None = None,
    ) -> None:
        with connection_context() as connection:
            connection.execute(
                """
                INSERT INTO audit_events (id, event_type, client_ip, path, action, resource_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    event_type,
                    client_ip,
                    path,
                    action,
                    resource_id,
                    utc_now_iso(),
                ),
            )

    def count_recent_events(self, *, event_type: str, client_ip: str, since_iso: str) -> int:
        with connection_context() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM audit_events
                WHERE event_type = ? AND client_ip = ? AND created_at >= ?
                """,
                (event_type, client_ip, since_iso),
            ).fetchone()
        return int(row['total'])

    def list_events(
        self,
        *,
        event_type: str | None = None,
        keyword: str | None = None,
        since_iso: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, object]:
        conditions: list[str] = []
        params: list[object] = []
        if event_type:
            conditions.append('event_type = ?')
            params.append(event_type)
        if keyword:
            conditions.append(
                "(client_ip LIKE ? OR path LIKE ? OR COALESCE(action, '') LIKE ? OR COALESCE(resource_id, '') LIKE ?)"
            )
            keyword_pattern = f'%{keyword}%'
            params.extend([keyword_pattern, keyword_pattern, keyword_pattern, keyword_pattern])
        if since_iso:
            conditions.append('created_at >= ?')
            params.append(since_iso)

        where_clause = f'WHERE {" AND ".join(conditions)}' if conditions else ''
        offset = (page - 1) * page_size

        with connection_context() as connection:
            total = connection.execute(
                f'SELECT COUNT(*) AS total FROM audit_events {where_clause}',
                params,
            ).fetchone()['total']
            rows = connection.execute(
                f"""
                SELECT id, event_type, client_ip, path, action, resource_id, created_at
                FROM audit_events
                {where_clause}
                ORDER BY created_at DESC, id DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()

        return {
            'items': [dict(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': total,
        }


class FeedbackRepository:
    def create_feedback(self, payload: FeedbackCreatePayload) -> FeedbackRecord:
        record = FeedbackRecord(
            id=new_feedback_id(),
            type=payload.type,
            related_id=payload.related_id,
            raw_content=payload.raw_content,
            expected_behavior=payload.expected_behavior,
            actual_behavior=payload.actual_behavior,
            page_url=payload.page_url,
            page_title=payload.page_title,
            environment_context=payload.environment_context,
            status=FeedbackStatus.PENDING,
            created_at=utc_now_iso(),
            submitted_at=None,
        )
        with connection_context() as connection:
            connection.execute(
                """
                INSERT INTO feedback_items (
                    id, type, related_id, expected_behavior, actual_behavior,
                    page_url, page_title, environment_context,
                    raw_content, status, created_at, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.type,
                    record.related_id,
                    record.expected_behavior,
                    record.actual_behavior,
                    record.page_url,
                    record.page_title,
                    record.environment_context,
                    record.raw_content,
                    record.status.value,
                    record.created_at,
                    record.submitted_at,
                ),
            )
        return record

    def list_feedback(
        self,
        *,
        status: FeedbackStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, object]:
        conditions: list[str] = []
        params: list[object] = []
        if status:
            conditions.append('feedback_items.status = ?')
            params.append(status.value)

        where_clause = f'WHERE {" AND ".join(conditions)}' if conditions else ''
        offset = (page - 1) * page_size

        with connection_context() as connection:
            total = connection.execute(
                f'SELECT COUNT(*) AS total FROM feedback_items {where_clause}',
                params,
            ).fetchone()['total']
            rows = connection.execute(
                f"""
                SELECT
                    feedback_items.id,
                    feedback_items.type,
                    feedback_items.related_id,
                    feedback_items.raw_content,
                    feedback_items.expected_behavior,
                    feedback_items.actual_behavior,
                    feedback_items.page_url,
                    feedback_items.page_title,
                    feedback_items.environment_context,
                    feedback_items.status,
                    feedback_items.created_at,
                    feedback_items.submitted_at,
                    draft_batches.id AS batch_id,
                    draft_batches.status AS batch_status,
                    draft_batches.integration_error AS batch_integration_error,
                    drafts.id AS draft_id,
                    drafts.status AS draft_status
                FROM feedback_items
                LEFT JOIN draft_batch_items ON draft_batch_items.feedback_item_id = feedback_items.id
                LEFT JOIN draft_batches ON draft_batches.id = draft_batch_items.batch_id
                LEFT JOIN drafts ON drafts.id = (
                    SELECT latest_drafts.id
                    FROM drafts AS latest_drafts
                    WHERE latest_drafts.batch_id = draft_batches.id
                    ORDER BY latest_drafts.updated_at DESC
                    LIMIT 1
                )
                {where_clause}
                ORDER BY feedback_items.created_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()

        return {
            'items': [dict(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': total,
        }

    def get_feedback_by_ids(self, feedback_ids: list[str]) -> list[FeedbackRecord]:
        if not feedback_ids:
            return []
        placeholders = ', '.join('?' for _ in feedback_ids)
        with connection_context() as connection:
            rows = connection.execute(
                f"""
                SELECT
                    id,
                    type,
                    related_id,
                    raw_content,
                    expected_behavior,
                    actual_behavior,
                    page_url,
                    page_title,
                    environment_context,
                    status,
                    created_at,
                    submitted_at
                FROM feedback_items
                WHERE id IN ({placeholders})
                ORDER BY created_at DESC
                """,
                feedback_ids,
            ).fetchall()
        return [FeedbackRecord(**dict(row)) for row in rows]

    def update_feedback_status(self, feedback_ids: list[str], status: FeedbackStatus) -> int:
        if not feedback_ids:
            return 0
        placeholders = ', '.join('?' for _ in feedback_ids)
        with connection_context() as connection:
            cursor = connection.execute(
                f'UPDATE feedback_items SET status = ? WHERE id IN ({placeholders})',
                [status.value, *feedback_ids],
            )
        return cursor.rowcount

    def mark_feedback_submitted(self, feedback_ids: list[str]) -> int:
        if not feedback_ids:
            return 0
        placeholders = ', '.join('?' for _ in feedback_ids)
        submitted_at = utc_now_iso()
        with connection_context() as connection:
            cursor = connection.execute(
                f'UPDATE feedback_items SET status = ?, submitted_at = ? WHERE id IN ({placeholders})',
                [FeedbackStatus.SUBMITTED.value, submitted_at, *feedback_ids],
            )
        return cursor.rowcount

    def count_recent_duplicate_feedback(self, payload: FeedbackCreatePayload, *, since_iso: str) -> int:
        with connection_context() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM feedback_items
                WHERE type = ?
                  AND related_id = ?
                  AND raw_content = ?
                  AND COALESCE(expected_behavior, '') = COALESCE(?, '')
                  AND COALESCE(actual_behavior, '') = COALESCE(?, '')
                  AND COALESCE(page_url, '') = COALESCE(?, '')
                  AND created_at >= ?
                """,
                (
                    payload.type,
                    payload.related_id,
                    payload.raw_content,
                    payload.expected_behavior,
                    payload.actual_behavior,
                    payload.page_url,
                    since_iso,
                ),
            ).fetchone()
        return int(row['total'])


class PublicFeedbackRateLimitRepository:
    def consume_daily_quota(self, *, ip_address: str, limit: int) -> bool:
        if limit <= 0:
            return False

        submit_date = datetime.now(timezone.utc).date().isoformat()
        updated_at = utc_now_iso()
        with connection_context() as connection:
            cursor = connection.execute(
                """
                INSERT INTO public_feedback_ip_limits (ip_address, submit_date, submission_count, updated_at)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(ip_address, submit_date) DO UPDATE SET
                    submission_count = submission_count + 1,
                    updated_at = excluded.updated_at
                WHERE public_feedback_ip_limits.submission_count < ?
                """,
                (ip_address, submit_date, updated_at, limit),
            )
        return cursor.rowcount == 1


class DraftBatchRepository:
    def create_batch(
        self,
        *,
        primary_related_id: str | None,
        related_id_count: int,
        status: DraftBatchStatus = DraftBatchStatus.CREATED,
    ) -> DraftBatchRecord:
        now = utc_now_iso()
        record = DraftBatchRecord(
            id=new_batch_id(),
            status=status,
            primary_related_id=primary_related_id,
            related_id_count=related_id_count,
            integration_error=None,
            created_at=now,
            updated_at=now,
        )
        with connection_context() as connection:
            connection.execute(
                """
                INSERT INTO draft_batches (id, status, primary_related_id, related_id_count, integration_error, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.status.value,
                    record.primary_related_id,
                    record.related_id_count,
                    record.integration_error,
                    record.created_at,
                    record.updated_at,
                ),
            )
        return record

    def attach_feedback_items(self, batch_id: str, feedback_ids: list[str]) -> list[DraftBatchItemRecord]:
        records: list[DraftBatchItemRecord] = []
        with connection_context() as connection:
            for feedback_id in feedback_ids:
                record = DraftBatchItemRecord(id=new_batch_item_id(), batch_id=batch_id, feedback_item_id=feedback_id)
                try:
                    connection.execute(
                        'INSERT INTO draft_batch_items (id, batch_id, feedback_item_id) VALUES (?, ?, ?)',
                        (record.id, record.batch_id, record.feedback_item_id),
                    )
                except sqlite3.IntegrityError as exc:
                    raise RepositoryError(f'Feedback item already belongs to an active batch: {feedback_id}') from exc
                records.append(record)
        return records

    def get_batch(self, batch_id: str) -> DraftBatchRecord | None:
        with connection_context() as connection:
            row = connection.execute(
                'SELECT id, status, primary_related_id, related_id_count, integration_error, created_at, updated_at FROM draft_batches WHERE id = ?',
                (batch_id,),
            ).fetchone()
        return DraftBatchRecord(**dict(row)) if row else None

    def update_batch_status(
        self,
        batch_id: str,
        *,
        status: DraftBatchStatus,
        integration_error: str | None = None,
    ) -> DraftBatchRecord | None:
        updated_at = utc_now_iso()
        with connection_context() as connection:
            connection.execute(
                'UPDATE draft_batches SET status = ?, integration_error = ?, updated_at = ? WHERE id = ?',
                (status.value, integration_error, updated_at, batch_id),
            )
        return self.get_batch(batch_id)

    def list_batch_feedback_items(self, batch_id: str) -> list[FeedbackRecord]:
        with connection_context() as connection:
            rows = connection.execute(
                """
                SELECT feedback_items.id, feedback_items.type, feedback_items.related_id, feedback_items.raw_content,
                       feedback_items.expected_behavior, feedback_items.actual_behavior,
                       feedback_items.page_url, feedback_items.page_title, feedback_items.environment_context,
                       feedback_items.status,
                       feedback_items.created_at, feedback_items.submitted_at
                FROM draft_batch_items
                JOIN feedback_items ON feedback_items.id = draft_batch_items.feedback_item_id
                WHERE draft_batch_items.batch_id = ?
                ORDER BY feedback_items.created_at ASC
                """,
                (batch_id,),
            ).fetchall()
        return [FeedbackRecord(**dict(row)) for row in rows]


class DraftBatchService:
    def __init__(self) -> None:
        self.feedback_repository = FeedbackRepository()
        self.batch_repository = DraftBatchRepository()

    def create_batch(self, feedback_ids: list[str], confirm_mixed_related_ids: bool) -> DraftBatchRecord:
        feedback_items = self.feedback_repository.get_feedback_by_ids(feedback_ids)

        if not feedback_items or len(feedback_items) != len(set(feedback_ids)):
            raise RepositoryError('Selected feedback items are missing')

        unique_related_ids = sorted({item.related_id for item in feedback_items})
        if len(unique_related_ids) > 1 and not confirm_mixed_related_ids:
            raise RepositoryError('Mixed related_id selection requires explicit confirmation')

        primary_related_id = unique_related_ids[0] if len(unique_related_ids) == 1 else None
        batch = self.batch_repository.create_batch(
            primary_related_id=primary_related_id,
            related_id_count=len(unique_related_ids),
        )
        self.batch_repository.attach_feedback_items(batch.id, feedback_ids)
        self.feedback_repository.update_feedback_status(feedback_ids, FeedbackStatus.GROUPED)
        return batch


class DraftIntegrationService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.batch_repository = DraftBatchRepository()
        self.draft_repository = DraftRepository()
        self.ai_client = OpenAICompatibleClient()

    def integrate_batch(self, batch_id: str) -> DraftRecord:
        batch = self.batch_repository.get_batch(batch_id)
        if not batch:
            raise RepositoryError('Draft batch not found')

        feedback_items = self.batch_repository.list_batch_feedback_items(batch_id)
        if not feedback_items:
            self.batch_repository.update_batch_status(
                batch_id,
                status=DraftBatchStatus.FAILED,
                integration_error='Draft batch has no feedback items',
            )
            raise RepositoryError('Draft batch has no feedback items')

        self.batch_repository.update_batch_status(batch_id, status=DraftBatchStatus.INTEGRATING)
        try:
            draft = self._build_draft(batch_id, feedback_items)
        except (RepositoryError, AIIntegrationError) as exc:
            self.batch_repository.update_batch_status(
                batch_id,
                status=DraftBatchStatus.FAILED,
                integration_error=str(exc),
            )
            raise RepositoryError(str(exc)) from exc

        self.batch_repository.update_batch_status(batch_id, status=DraftBatchStatus.DRAFT_READY)
        return draft

    def _build_draft(self, batch_id: str, feedback_items: list[FeedbackRecord]) -> DraftRecord:
        related_ids = sorted({item.related_id for item in feedback_items})
        primary_related_id = related_ids[0] if len(related_ids) == 1 else 'mixed-related-ids'
        issue_type = self._issue_type_label(feedback_items[0].type)
        related_id_summary = ', '.join(related_ids)
        prompt_snapshot = self._build_prompt_snapshot(feedback_items)
        if self._should_use_ai():
            try:
                generated = self.ai_client.create_issue_draft(
                    prompt_snapshot=prompt_snapshot, feedback_items=feedback_items
                )
                title = generated['title']
                body_markdown = generated['body_markdown']
                ai_model = self.settings.ai_model
            except AIIntegrationError:
                title = f'[{issue_type}] {primary_related_id}'
                body_markdown = self._build_markdown(primary_related_id, feedback_items)
                ai_model = 'deterministic-template-v1'
        else:
            title = f'[{issue_type}] {primary_related_id}'
            body_markdown = self._build_markdown(primary_related_id, feedback_items)
            ai_model = 'deterministic-template-v1'
        return self.draft_repository.create_draft(
            batch_id=batch_id,
            title=title,
            body_markdown=body_markdown,
            related_id_summary=related_id_summary,
            ai_model=ai_model,
            prompt_snapshot=prompt_snapshot,
        )

    def _should_use_ai(self) -> bool:
        return bool(self.settings.ai_api_key and self.settings.ai_api_base_url and self.settings.ai_model)

    def _build_prompt_snapshot(self, feedback_items: list[FeedbackRecord]) -> str:
        lines = []
        for item in feedback_items:
            details = [
                f'类型: {self._issue_type_label(item.type)}',
                f'关联标识: {item.related_id}',
                f'反馈内容: {item.raw_content}',
            ]
            if item.expected_behavior:
                details.append(f'期望表现: {item.expected_behavior}')
            if item.actual_behavior:
                details.append(f'实际表现: {item.actual_behavior}')
            if item.page_title:
                details.append(f'页面标题: {item.page_title}')
            if item.page_url:
                details.append(f'页面链接: {item.page_url}')
            if item.environment_context:
                details.append(f'运行环境: {item.environment_context}')
            lines.append('- ' + ' | '.join(details))
        return '\n'.join(lines)

    def _issue_type_label(self, issue_type: str) -> str:
        return {
            'bug': '缺陷',
            'feature': '新功能',
            'enhancement': '优化',
            'question': '问题',
        }.get(issue_type, issue_type)

    def _build_markdown(self, primary_related_id: str, feedback_items: list[FeedbackRecord]) -> str:
        summary_lines = [f'- {item.raw_content}' for item in feedback_items]
        background_lines = [f'- {self._issue_type_label(item.type)}：{item.raw_content}' for item in feedback_items]
        steps_lines = []
        expected_lines = []
        actual_lines = []
        missing_lines = []

        for index, item in enumerate(feedback_items, start=1):
            if item.expected_behavior and item.actual_behavior:
                steps_lines.append(f'{index}. 根据反馈 {item.id} 复现关联流程：{item.related_id}。')
            context_fragments = self._build_context_fragments(item)
            if context_fragments:
                background_lines.append(f'- 反馈 {item.id} 上下文：{" | ".join(context_fragments)}')
            if item.expected_behavior:
                expected_lines.append(f'- {item.expected_behavior}')
            else:
                missing_lines.append(f'- 反馈 {item.id} 缺少期望表现。')
            if item.actual_behavior:
                actual_lines.append(f'- {item.actual_behavior}')
            else:
                missing_lines.append(f'- 反馈 {item.id} 缺少实际表现。')

        if not steps_lines:
            steps_lines.append('1. 当前反馈未提供完整复现步骤，需要根据关联标识定位对应流程后补充。')
            missing_lines.append('- 所选反馈缺少可直接执行的复现步骤。')
        if not expected_lines:
            expected_lines.append('- 当前反馈未提供明确期望表现。')
        if not actual_lines:
            actual_lines.append('- 当前反馈未提供明确实际表现。')
        if not missing_lines:
            missing_lines.append('- 暂未发现影响初步排查的关键信息缺口。')

        return '\n\n'.join(
            [
                '## 摘要\n' + '\n'.join(summary_lines),
                f'## 关联标识\n{primary_related_id}',
                f'## 用户反馈数量\n{len(feedback_items)}',
                '## 背景\n' + '\n'.join(background_lines),
                '## 复现线索\n' + '\n'.join(steps_lines),
                '## 期望表现\n' + '\n'.join(expected_lines),
                '## 实际表现\n' + '\n'.join(actual_lines),
                '## 影响范围\n- 多条用户反馈指向该关联流程，建议优先确认是否影响主路径体验。',
                '## 待补充信息\n' + '\n'.join(missing_lines),
                '## 原始反馈\n' + '\n'.join(summary_lines),
            ]
        )

    def _build_context_fragments(self, item: FeedbackRecord) -> list[str]:
        fragments: list[str] = []
        if item.page_title:
            fragments.append(f'页面标题：{item.page_title}')
        if item.page_url:
            fragments.append(f'页面链接：{item.page_url}')
        if item.environment_context:
            fragments.append(f'运行环境：{item.environment_context}')
        return fragments


class AIIntegrationError(ValueError):
    pass


class OpenAICompatibleClient:
    REQUIRED_SECTION_HEADINGS = (
        '## 摘要',
        '## 关联标识',
        '## 用户反馈数量',
        '## 背景',
        '## 复现线索',
        '## 期望表现',
        '## 实际表现',
        '## 影响范围',
        '## 待补充信息',
        '## 原始反馈',
    )

    def __init__(self) -> None:
        self.settings = get_settings()

    def create_issue_draft(self, *, prompt_snapshot: str, feedback_items: list[FeedbackRecord]) -> dict[str, str]:
        if not self.settings.ai_api_key:
            raise AIIntegrationError('AI_API_KEY is required')
        if not self.settings.ai_api_base_url or not self.settings.ai_model:
            raise AIIntegrationError('AI_API_BASE_URL and AI_MODEL are required')

        endpoint = self._build_chat_completions_endpoint(self.settings.ai_api_base_url)
        payload = json.dumps(
            {
                'model': self.settings.ai_model,
                'temperature': 0.2,
                'max_completion_tokens': 2400,
                'stream': False,
                'messages': [
                    {
                        'role': 'system',
                        'content': (
                            '你是产品问题整理助手，负责把多条用户反馈整理成一条可直接提交到 GitHub 的中文 Issue。'
                            '只返回严格 JSON，字段只能包含 title 和 body_markdown。'
                            '不要使用 markdown 代码块包裹 JSON。'
                        ),
                    },
                    {
                        'role': 'user',
                        'content': self._build_user_prompt(
                            prompt_snapshot=prompt_snapshot, feedback_items=feedback_items
                        ),
                    },
                ],
            }
        ).encode('utf-8')
        http_request = request.Request(
            endpoint,
            data=payload,
            method='POST',
            headers={
                'Authorization': f'Bearer {self.settings.ai_api_key}',
                'Content-Type': 'application/json',
                'User-Agent': 'issue-aggregator-mvp',
            },
        )

        try:
            with request.urlopen(http_request, timeout=60) as response:
                response_body = json.loads(response.read().decode('utf-8'))
        except TimeoutError as exc:
            raise AIIntegrationError('AI API request timed out') from exc
        except error.HTTPError as exc:
            raise AIIntegrationError(f'AI API request failed with status {exc.code}') from exc
        except error.URLError as exc:
            raise AIIntegrationError(str(exc.reason)) from exc
        except json.JSONDecodeError as exc:
            raise AIIntegrationError('AI API returned invalid JSON') from exc

        content = self._extract_message_content(response_body)
        parsed = self._parse_json_content(content)

        title = str(parsed.get('title', '')).strip()
        body_markdown = str(parsed.get('body_markdown', '')).strip()
        if not title or not body_markdown:
            raise AIIntegrationError('AI response must include title and body_markdown')
        self._validate_issue_draft(title=title, body_markdown=body_markdown)
        return {'title': title[:200], 'body_markdown': body_markdown}

    def _build_chat_completions_endpoint(self, base_url: str) -> str:
        normalized = base_url.rstrip('/')
        if normalized.endswith('/chat/completions'):
            return normalized
        return f'{normalized}/chat/completions'

    def _build_user_prompt(self, *, prompt_snapshot: str, feedback_items: list[FeedbackRecord]) -> str:
        return '\n\n'.join(
            [
                '请根据以下已分组用户反馈，生成一条中文 GitHub Issue 草稿。',
                '输出要求：',
                '- title 使用中文，格式为：[缺陷] 具体问题、[优化] 具体改进、[新功能] 具体能力或 [问题] 具体疑问。',
                '- title 控制在 50 个中文字符以内，避免泛泛描述。',
                '- body_markdown 使用中文 Markdown。',
                '- body_markdown 必须包含这些二级标题：摘要、关联标识、用户反馈数量、背景、复现线索、期望表现、实际表现、影响范围、待补充信息、原始反馈。',
                '- 保留用户反馈里的具体场景、症状、期望和实际表现。',
                '- 对缺失信息明确写入待补充信息，不要编造复现步骤、错误码或环境。',
                '- 多条反馈表达同一问题时合并归纳，保留关键差异。',
                f'用户反馈数量：{len(feedback_items)}',
                '反馈项：',
                prompt_snapshot,
            ]
        )

    def _extract_message_content(self, response_body: dict[str, object]) -> str:
        choices = response_body.get('choices')
        if not isinstance(choices, list) or not choices:
            raise AIIntegrationError('AI API response has no choices')
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise AIIntegrationError('AI API response choice is invalid')
        message = first_choice.get('message')
        if not isinstance(message, dict):
            raise AIIntegrationError('AI API response message is invalid')
        content = message.get('content')
        if not isinstance(content, str) or not content.strip():
            raise AIIntegrationError('AI API response content is empty')
        return content.strip()

    def _parse_json_content(self, content: str) -> dict[str, object]:
        normalized = content.strip()
        if normalized.startswith('```'):
            lines = normalized.splitlines()
            if lines and lines[0].startswith('```'):
                lines = lines[1:]
            if lines and lines[-1].strip() == '```':
                lines = lines[:-1]
            normalized = '\n'.join(lines).strip()
        try:
            parsed = json.loads(normalized)
        except json.JSONDecodeError as exc:
            raise AIIntegrationError('AI response content is not valid JSON') from exc
        if not isinstance(parsed, dict):
            raise AIIntegrationError('AI response JSON must be an object')
        return parsed

    def _validate_issue_draft(self, *, title: str, body_markdown: str) -> None:
        valid_prefixes = ('[缺陷]', '[优化]', '[新功能]', '[问题]')
        if not title.startswith(valid_prefixes):
            raise AIIntegrationError('AI response title did not follow the required Chinese format')

        missing_headings = [heading for heading in self.REQUIRED_SECTION_HEADINGS if heading not in body_markdown]
        if missing_headings:
            raise AIIntegrationError(
                'AI response body did not include required headings: ' + ', '.join(missing_headings)
            )


class DraftRepository:
    def create_draft(
        self,
        *,
        batch_id: str,
        title: str,
        body_markdown: str,
        related_id_summary: str,
        status: DraftStatus = DraftStatus.DRAFT_READY,
        ai_model: str | None = None,
        prompt_snapshot: str | None = None,
    ) -> DraftRecord:
        record = DraftRecord(
            id=new_draft_id(),
            batch_id=batch_id,
            title=title,
            body_markdown=body_markdown,
            related_id_summary=related_id_summary,
            status=status,
            ai_model=ai_model,
            prompt_snapshot=prompt_snapshot,
            updated_at=utc_now_iso(),
        )
        with connection_context() as connection:
            connection.execute(
                """
                INSERT INTO drafts (id, batch_id, title, body_markdown, related_id_summary, status, ai_model, prompt_snapshot, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.batch_id,
                    record.title,
                    record.body_markdown,
                    record.related_id_summary,
                    record.status.value,
                    record.ai_model,
                    record.prompt_snapshot,
                    record.updated_at,
                ),
            )
        return record

    def get_draft(self, draft_id: str) -> DraftRecord | None:
        with connection_context() as connection:
            row = connection.execute(
                'SELECT id, batch_id, title, body_markdown, related_id_summary, status, ai_model, prompt_snapshot, updated_at FROM drafts WHERE id = ?',
                (draft_id,),
            ).fetchone()
        return DraftRecord(**dict(row)) if row else None

    def get_draft_by_batch_id(self, batch_id: str) -> DraftRecord | None:
        with connection_context() as connection:
            row = connection.execute(
                'SELECT id, batch_id, title, body_markdown, related_id_summary, status, ai_model, prompt_snapshot, updated_at FROM drafts WHERE batch_id = ? ORDER BY updated_at DESC LIMIT 1',
                (batch_id,),
            ).fetchone()
        return DraftRecord(**dict(row)) if row else None

    def update_draft(self, draft_id: str, payload: DraftUpdatePayload) -> DraftRecord | None:
        updated_at = utc_now_iso()
        with connection_context() as connection:
            connection.execute(
                'UPDATE drafts SET title = ?, body_markdown = ?, updated_at = ? WHERE id = ?',
                (payload.title, payload.body_markdown, updated_at, draft_id),
            )
        return self.get_draft(draft_id)

    def update_draft_status(self, draft_id: str, status: DraftStatus) -> DraftRecord | None:
        updated_at = utc_now_iso()
        with connection_context() as connection:
            connection.execute(
                'UPDATE drafts SET status = ?, updated_at = ? WHERE id = ?',
                (status.value, updated_at, draft_id),
            )
        return self.get_draft(draft_id)


class SubmissionRepository:
    def list_submitted_issues(
        self,
        *,
        page: int,
        page_size: int,
        related_id: str | None = None,
        issue_type: str | None = None,
        keyword: str | None = None,
    ) -> dict[str, object]:
        conditions: list[str] = []
        params: list[object] = []

        if related_id:
            conditions.append('submissions.related_id = ?')
            params.append(related_id)
        if issue_type:
            conditions.append('feedback_items.type = ?')
            params.append(issue_type)
        if keyword:
            like_value = f'%{keyword.strip()}%'
            conditions.append('(drafts.title LIKE ? OR drafts.body_markdown LIKE ? OR submissions.related_id LIKE ?)')
            params.extend([like_value, like_value, like_value])

        conditions.append('submissions.response_status >= 200 AND submissions.response_status < 300')
        where_clause = f'WHERE {" AND ".join(conditions)}' if conditions else ''
        offset = (page - 1) * page_size

        with connection_context() as connection:
            total = connection.execute(
                f"""
                SELECT COUNT(DISTINCT submissions.id) AS total
                FROM submissions
                JOIN drafts ON drafts.id = submissions.draft_id
                LEFT JOIN draft_batches ON draft_batches.id = drafts.batch_id
                LEFT JOIN draft_batch_items ON draft_batch_items.batch_id = draft_batches.id
                LEFT JOIN feedback_items ON feedback_items.id = draft_batch_items.feedback_item_id
                {where_clause}
                """,
                params,
            ).fetchone()['total']

            rows = connection.execute(
                f"""
                SELECT
                    submissions.github_issue_number AS issue_number,
                    drafts.title AS title,
                    submissions.github_issue_url AS issue_url,
                    submissions.related_id AS related_id,
                    CASE
                        WHEN COUNT(DISTINCT feedback_items.type) = 0 THEN 'bug'
                        WHEN COUNT(DISTINCT feedback_items.type) = 1 THEN MIN(feedback_items.type)
                        ELSE 'mixed'
                    END AS type,
                    submissions.submitted_at AS submitted_at
                FROM submissions
                JOIN drafts ON drafts.id = submissions.draft_id
                LEFT JOIN draft_batches ON draft_batches.id = drafts.batch_id
                LEFT JOIN draft_batch_items ON draft_batch_items.batch_id = draft_batches.id
                LEFT JOIN feedback_items ON feedback_items.id = draft_batch_items.feedback_item_id
                {where_clause}
                GROUP BY submissions.id, drafts.title, submissions.github_issue_number, submissions.github_issue_url, submissions.related_id, submissions.submitted_at
                ORDER BY submissions.submitted_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()

        return {
            'items': [dict(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': total,
        }

    def create_submission_fixture(
        self,
        *,
        draft_id: str,
        issue_number: int,
        issue_url: str,
        related_id: str,
        submitted_at: str,
        title: str,
        issue_type: str,
    ) -> None:
        with connection_context() as connection:
            connection.execute(
                'INSERT OR IGNORE INTO draft_batches (id, status, primary_related_id, related_id_count, integration_error, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
                ('batch_fixture', 'submitted', related_id, 1, None, submitted_at, submitted_at),
            )
            connection.execute(
                'INSERT OR IGNORE INTO feedback_items (id, type, related_id, expected_behavior, actual_behavior, raw_content, status, created_at, submitted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    f'fb_fixture_{issue_number}',
                    issue_type,
                    related_id,
                    None,
                    None,
                    title,
                    FeedbackStatus.SUBMITTED.value,
                    submitted_at,
                    submitted_at,
                ),
            )
            connection.execute(
                'INSERT OR IGNORE INTO draft_batch_items (id, batch_id, feedback_item_id) VALUES (?, ?, ?)',
                (f'dbi_{issue_number}', 'batch_fixture', f'fb_fixture_{issue_number}'),
            )
            connection.execute(
                'INSERT OR REPLACE INTO drafts (id, batch_id, title, body_markdown, related_id_summary, status, ai_model, prompt_snapshot, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (draft_id, 'batch_fixture', title, title, related_id, 'submitted', None, None, submitted_at),
            )
            connection.execute(
                'INSERT OR REPLACE INTO submissions (id, draft_id, github_issue_number, github_issue_url, related_id, github_state, labels_snapshot, response_status, submitted_at, error_summary) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (
                    f'sub_{issue_number}',
                    draft_id,
                    issue_number,
                    issue_url,
                    related_id,
                    'open',
                    None,
                    201,
                    submitted_at,
                    None,
                ),
            )

    def create_submission(
        self,
        *,
        draft_id: str,
        github_issue_number: int,
        github_issue_url: str,
        related_id: str,
        response_status: int,
        github_state: str | None = None,
        labels_snapshot: str | None = None,
        error_summary: str | None = None,
    ) -> SubmissionRecord:
        record = SubmissionRecord(
            id=new_submission_id(),
            draft_id=draft_id,
            github_issue_number=github_issue_number,
            github_issue_url=github_issue_url,
            related_id=related_id,
            github_state=github_state,
            labels_snapshot=labels_snapshot,
            response_status=response_status,
            submitted_at=utc_now_iso(),
            error_summary=error_summary,
        )
        with connection_context() as connection:
            connection.execute(
                """
                INSERT INTO submissions (id, draft_id, github_issue_number, github_issue_url, related_id, github_state, labels_snapshot, response_status, submitted_at, error_summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.draft_id,
                    record.github_issue_number,
                    record.github_issue_url,
                    record.related_id,
                    record.github_state,
                    record.labels_snapshot,
                    record.response_status,
                    record.submitted_at,
                    record.error_summary,
                ),
            )
        return record

    def count_recent_submissions(self, *, related_id: str | None = None, since_iso: str) -> int:
        conditions = ['submitted_at >= ?', 'response_status >= 200 AND response_status < 300']
        params: list[object] = [since_iso]
        if related_id:
            conditions.append('related_id = ?')
            params.append(related_id)
        where_clause = f'WHERE {" AND ".join(conditions)}'
        with connection_context() as connection:
            row = connection.execute(
                f'SELECT COUNT(*) AS total FROM submissions {where_clause}',
                params,
            ).fetchone()
        return row['total']


class GitHubSubmissionError(ValueError):
    pass


class GitHubIssueClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def create_issue(self, *, title: str, body: str) -> dict[str, object]:
        if not self.settings.github_token:
            raise GitHubSubmissionError('GITHUB_TOKEN is required')
        if not self.settings.github_repo_owner or not self.settings.github_repo_name:
            raise GitHubSubmissionError('GitHub repository settings are required')

        endpoint = (
            f'https://api.github.com/repos/{self.settings.github_repo_owner}/{self.settings.github_repo_name}/issues'
        )
        payload = json.dumps({'title': title, 'body': body}).encode('utf-8')
        http_request = request.Request(
            endpoint,
            data=payload,
            method='POST',
            headers={
                'Accept': 'application/vnd.github+json',
                'Authorization': f'Bearer {self.settings.github_token}',
                'Content-Type': 'application/json',
                'User-Agent': 'issue-aggregator-mvp',
            },
        )

        try:
            with request.urlopen(http_request, timeout=15) as response:
                response_body = json.loads(response.read().decode('utf-8'))
                return {
                    'issue_number': response_body['number'],
                    'issue_url': response_body['html_url'],
                    'related_id': response_body.get('body', ''),
                    'response_status': response.status,
                    'github_state': response_body.get('state'),
                }
        except error.HTTPError as exc:
            raise GitHubSubmissionError(f'GitHub API request failed with status {exc.code}') from exc
        except error.URLError as exc:
            raise GitHubSubmissionError(str(exc.reason)) from exc


class DraftSubmissionService:
    MAX_GITHUB_TITLE_LENGTH = 160
    MAX_GITHUB_BODY_LENGTH = 12000
    SENSITIVE_CONTENT_PATTERNS = (
        re.compile(r'gh[pousr]_[A-Za-z0-9]{20,}'),
        re.compile(r'glpat-[A-Za-z0-9_-]{20,}'),
        re.compile(r'sk-[A-Za-z0-9]{20,}'),
        re.compile(r'AKIA[0-9A-Z]{16}'),
        re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'),
        re.compile(r'authorization\s*:\s*bearer\s+[A-Za-z0-9._\-]+', re.IGNORECASE),
    )

    def __init__(self) -> None:
        self.settings = get_settings()
        self.batch_repository = DraftBatchRepository()
        self.draft_repository = DraftRepository()
        self.feedback_repository = FeedbackRepository()
        self.submission_repository = SubmissionRepository()
        self.github_client = GitHubIssueClient()

    def submit_draft(self, draft_id: str) -> SubmissionRecord:
        draft = self.draft_repository.get_draft(draft_id)
        if not draft:
            raise RepositoryError('Draft not found')

        batch = self.batch_repository.get_batch(draft.batch_id)
        if not batch:
            raise RepositoryError('Draft batch not found')

        self._validate_draft_content(draft)
        self._enforce_rate_limits(draft.related_id_summary)

        try:
            github_response = self.github_client.create_issue(title=draft.title, body=draft.body_markdown)
        except GitHubSubmissionError as exc:
            self.draft_repository.update_draft_status(draft.id, DraftStatus.FAILED)
            self.batch_repository.update_batch_status(
                batch.id,
                status=DraftBatchStatus.FAILED,
                integration_error=str(exc),
            )
            self.submission_repository.create_submission(
                draft_id=draft.id,
                github_issue_number=0,
                github_issue_url='',
                related_id=draft.related_id_summary,
                response_status=500,
                error_summary=str(exc),
            )
            raise RepositoryError(str(exc)) from exc

        feedback_items = self.batch_repository.list_batch_feedback_items(batch.id)
        self.feedback_repository.mark_feedback_submitted([item.id for item in feedback_items])
        self.draft_repository.update_draft_status(draft.id, DraftStatus.SUBMITTED)
        self.batch_repository.update_batch_status(batch.id, status=DraftBatchStatus.SUBMITTED)
        return self.submission_repository.create_submission(
            draft_id=draft.id,
            github_issue_number=int(github_response['issue_number']),
            github_issue_url=str(github_response['issue_url']),
            related_id=batch.primary_related_id or draft.related_id_summary,
            response_status=int(github_response['response_status']),
            github_state=str(github_response.get('github_state') or 'open'),
        )

    def _enforce_rate_limits(self, related_id_summary: str) -> None:
        now = datetime.now(timezone.utc)
        global_since = (now - timedelta(hours=1)).replace(microsecond=0).isoformat().replace('+00:00', 'Z')
        total_recent = self.submission_repository.count_recent_submissions(since_iso=global_since)
        if total_recent >= self.settings.rate_limit_per_hour:
            raise RepositoryError('Submission rate limit reached')

        related_ids = [item.strip() for item in related_id_summary.split(',') if item.strip()]
        related_since = (
            (now - timedelta(hours=self.settings.related_id_rate_limit_window))
            .replace(microsecond=0)
            .isoformat()
            .replace('+00:00', 'Z')
        )
        for related_id in related_ids:
            per_related_count = self.submission_repository.count_recent_submissions(
                related_id=related_id,
                since_iso=related_since,
            )
            if per_related_count > 0:
                raise RepositoryError(f'related_id rate limit reached for {related_id}')

    def _validate_draft_content(self, draft: DraftRecord) -> None:
        if len(draft.title) > self.MAX_GITHUB_TITLE_LENGTH:
            raise RepositoryError('Draft title exceeds safe submission limit')
        if len(draft.body_markdown) > self.MAX_GITHUB_BODY_LENGTH:
            raise RepositoryError('Draft body exceeds safe submission limit')

        combined_content = f'{draft.title}\n{draft.body_markdown}'
        for pattern in self.SENSITIVE_CONTENT_PATTERNS:
            if pattern.search(combined_content):
                raise RepositoryError('Draft content contains sensitive credential-like content')


class AdminSessionRepository:
    def create_session(
        self, *, session_token_hash: str, username: str, client_ip: str | None, user_agent_summary: str | None
    ) -> AdminSessionRecord:
        from .config import get_settings

        settings = get_settings()
        now = datetime.now(timezone.utc)
        idle_expires = now + timedelta(minutes=settings.admin_session_idle_minutes)
        absolute_expires = now + timedelta(hours=settings.admin_session_max_hours)
        session_id = f'sess_{uuid4().hex[:12]}'

        with connection_context() as connection:
            connection.execute(
                """
                INSERT INTO admin_sessions (id, session_token_hash, username, client_ip, user_agent_summary, created_at, last_seen_at, idle_expires_at, absolute_expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    session_token_hash,
                    username,
                    client_ip,
                    user_agent_summary,
                    utc_now_iso(),
                    utc_now_iso(),
                    idle_expires.replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
                    absolute_expires.replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
                ),
            )
        return AdminSessionRecord(
            id=session_id,
            session_token_hash=session_token_hash,
            username=username,
            client_ip=client_ip,
            user_agent_summary=user_agent_summary,
            created_at=utc_now_iso(),
            last_seen_at=utc_now_iso(),
            idle_expires_at=idle_expires.replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
            absolute_expires_at=absolute_expires.replace(microsecond=0).isoformat().replace('+00:00', 'Z'),
            revoked_at=None,
        )

    def find_active_session(self, session_token_hash: str) -> AdminSessionRecord | None:
        now_iso = utc_now_iso()
        with connection_context() as connection:
            row = connection.execute(
                """
                SELECT * FROM admin_sessions
                WHERE session_token_hash = ?
                  AND revoked_at IS NULL
                  AND idle_expires_at > ?
                  AND absolute_expires_at > ?
                """,
                (session_token_hash, now_iso, now_iso),
            ).fetchone()
        if row is None:
            return None
        return AdminSessionRecord(
            id=row['id'],
            session_token_hash=row['session_token_hash'],
            username=row['username'],
            client_ip=row['client_ip'],
            user_agent_summary=row['user_agent_summary'],
            created_at=row['created_at'],
            last_seen_at=row['last_seen_at'],
            idle_expires_at=row['idle_expires_at'],
            absolute_expires_at=row['absolute_expires_at'],
            revoked_at=row['revoked_at'],
        )

    def find_by_token_hash(self, session_token_hash: str) -> AdminSessionRecord | None:
        with connection_context() as connection:
            row = connection.execute(
                'SELECT * FROM admin_sessions WHERE session_token_hash = ? LIMIT 1',
                (session_token_hash,),
            ).fetchone()
        if row is None:
            return None
        return AdminSessionRecord(
            id=row['id'],
            session_token_hash=row['session_token_hash'],
            username=row['username'],
            client_ip=row['client_ip'],
            user_agent_summary=row['user_agent_summary'],
            created_at=row['created_at'],
            last_seen_at=row['last_seen_at'],
            idle_expires_at=row['idle_expires_at'],
            absolute_expires_at=row['absolute_expires_at'],
            revoked_at=row['revoked_at'],
        )

    def touch_session(self, session_token_hash: str) -> bool:
        from .config import get_settings

        settings = get_settings()
        now_iso = utc_now_iso()
        idle_expires = (
            (datetime.now(timezone.utc) + timedelta(minutes=settings.admin_session_idle_minutes))
            .replace(microsecond=0)
            .isoformat()
            .replace('+00:00', 'Z')
        )
        with connection_context() as connection:
            cursor = connection.execute(
                """
                UPDATE admin_sessions
                SET last_seen_at = ?, idle_expires_at = ?
                WHERE session_token_hash = ?
                  AND revoked_at IS NULL
                  AND absolute_expires_at > ?
                """,
                (now_iso, idle_expires, session_token_hash, now_iso),
            )
        return cursor.rowcount > 0

    def revoke_session(self, session_token_hash: str) -> bool:
        now_iso = utc_now_iso()
        with connection_context() as connection:
            cursor = connection.execute(
                'UPDATE admin_sessions SET revoked_at = ? WHERE session_token_hash = ? AND revoked_at IS NULL',
                (now_iso, session_token_hash),
            )
        return cursor.rowcount > 0


class AdminLoginAttemptRepository:
    LOGIN_RESULT_SUCCESS = 'success'
    LOGIN_RESULT_FAILURE = 'failure'
    LOGIN_RESULT_COOLDOWN = 'cooldown_blocked'

    def record_attempt(self, *, username: str, client_ip: str | None, result: str, reason: str | None = None) -> str:
        attempt_id = f'la_{uuid4().hex[:12]}'
        with connection_context() as connection:
            connection.execute(
                """
                INSERT INTO admin_login_attempts (id, username, client_ip, result, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (attempt_id, username, client_ip, result, reason, utc_now_iso()),
            )
        return attempt_id

    def count_recent_failures(self, *, client_ip: str, since_iso: str) -> int:
        with connection_context() as connection:
            row = connection.execute(
                """
                SELECT COUNT(*) AS total FROM admin_login_attempts
                WHERE client_ip = ? AND result = ? AND created_at >= ?
                """,
                (client_ip, self.LOGIN_RESULT_FAILURE, since_iso),
            ).fetchone()
        return int(row['total'])

    def last_attempt_after(self, *, client_ip: str, since_iso: str) -> AdminLoginAttemptRecord | None:
        with connection_context() as connection:
            row = connection.execute(
                """
                SELECT * FROM admin_login_attempts
                WHERE client_ip = ? AND created_at >= ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (client_ip, since_iso),
            ).fetchone()
        if row is None:
            return None
        return AdminLoginAttemptRecord(
            id=row['id'],
            username=row['username'],
            client_ip=row['client_ip'],
            result=row['result'],
            reason=row['reason'],
            created_at=row['created_at'],
        )
