from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from urllib import error, request

from .config import get_settings

from .database import connection_context
from .models import (
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


class FeedbackRepository:
    def create_feedback(self, payload: FeedbackCreatePayload) -> FeedbackRecord:
        record = FeedbackRecord(
            id=new_feedback_id(),
            type=payload.type,
            related_id=payload.related_id,
            raw_content=payload.raw_content,
            expected_behavior=payload.expected_behavior,
            actual_behavior=payload.actual_behavior,
            status=FeedbackStatus.PENDING,
            created_at=utc_now_iso(),
            submitted_at=None,
        )
        with connection_context() as connection:
            connection.execute(
                """
                INSERT INTO feedback_items (
                    id, type, related_id, expected_behavior, actual_behavior,
                    raw_content, status, created_at, submitted_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.type,
                    record.related_id,
                    record.expected_behavior,
                    record.actual_behavior,
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
            conditions.append("status = ?")
            params.append(status.value)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * page_size

        with connection_context() as connection:
            total = connection.execute(
                f"SELECT COUNT(*) AS total FROM feedback_items {where_clause}",
                params,
            ).fetchone()["total"]
            rows = connection.execute(
                f"""
                SELECT id, type, related_id, raw_content, expected_behavior, actual_behavior, status, created_at, submitted_at
                FROM feedback_items
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()

        return {
            "items": [dict(row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    def get_feedback_by_ids(self, feedback_ids: list[str]) -> list[FeedbackRecord]:
        if not feedback_ids:
            return []
        placeholders = ", ".join("?" for _ in feedback_ids)
        with connection_context() as connection:
            rows = connection.execute(
                f"""
                SELECT id, type, related_id, raw_content, expected_behavior, actual_behavior, status, created_at, submitted_at
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
        placeholders = ", ".join("?" for _ in feedback_ids)
        with connection_context() as connection:
            cursor = connection.execute(
                f"UPDATE feedback_items SET status = ? WHERE id IN ({placeholders})",
                [status.value, *feedback_ids],
            )
        return cursor.rowcount

    def mark_feedback_submitted(self, feedback_ids: list[str]) -> int:
        if not feedback_ids:
            return 0
        placeholders = ", ".join("?" for _ in feedback_ids)
        submitted_at = utc_now_iso()
        with connection_context() as connection:
            cursor = connection.execute(
                f"UPDATE feedback_items SET status = ?, submitted_at = ? WHERE id IN ({placeholders})",
                [FeedbackStatus.SUBMITTED.value, submitted_at, *feedback_ids],
            )
        return cursor.rowcount


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
                        "INSERT INTO draft_batch_items (id, batch_id, feedback_item_id) VALUES (?, ?, ?)",
                        (record.id, record.batch_id, record.feedback_item_id),
                    )
                except sqlite3.IntegrityError as exc:
                    raise RepositoryError(f"Feedback item already belongs to an active batch: {feedback_id}") from exc
                records.append(record)
        return records

    def get_batch(self, batch_id: str) -> DraftBatchRecord | None:
        with connection_context() as connection:
            row = connection.execute(
                "SELECT id, status, primary_related_id, related_id_count, integration_error, created_at, updated_at FROM draft_batches WHERE id = ?",
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
                "UPDATE draft_batches SET status = ?, integration_error = ?, updated_at = ? WHERE id = ?",
                (status.value, integration_error, updated_at, batch_id),
            )
        return self.get_batch(batch_id)

    def list_batch_feedback_items(self, batch_id: str) -> list[FeedbackRecord]:
        with connection_context() as connection:
            rows = connection.execute(
                """
                SELECT feedback_items.id, feedback_items.type, feedback_items.related_id, feedback_items.raw_content,
                       feedback_items.expected_behavior, feedback_items.actual_behavior, feedback_items.status,
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
            raise RepositoryError("Selected feedback items are missing")

        unique_related_ids = sorted({item.related_id for item in feedback_items})
        if len(unique_related_ids) > 1 and not confirm_mixed_related_ids:
            raise RepositoryError("Mixed related_id selection requires explicit confirmation")

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
        self.batch_repository = DraftBatchRepository()
        self.draft_repository = DraftRepository()

    def integrate_batch(self, batch_id: str) -> DraftRecord:
        batch = self.batch_repository.get_batch(batch_id)
        if not batch:
            raise RepositoryError("Draft batch not found")

        feedback_items = self.batch_repository.list_batch_feedback_items(batch_id)
        if not feedback_items:
            self.batch_repository.update_batch_status(
                batch_id,
                status=DraftBatchStatus.FAILED,
                integration_error="Draft batch has no feedback items",
            )
            raise RepositoryError("Draft batch has no feedback items")

        self.batch_repository.update_batch_status(batch_id, status=DraftBatchStatus.INTEGRATING)
        try:
            draft = self._build_draft(batch_id, feedback_items)
        except RepositoryError as exc:
            self.batch_repository.update_batch_status(
                batch_id,
                status=DraftBatchStatus.FAILED,
                integration_error=str(exc),
            )
            raise

        self.batch_repository.update_batch_status(batch_id, status=DraftBatchStatus.DRAFT_READY)
        return draft

    def _build_draft(self, batch_id: str, feedback_items: list[FeedbackRecord]) -> DraftRecord:
        related_ids = sorted({item.related_id for item in feedback_items})
        primary_related_id = related_ids[0] if len(related_ids) == 1 else "mixed-related-ids"
        issue_type = feedback_items[0].type.capitalize()
        title = f"[{issue_type}] {primary_related_id}"
        related_id_summary = ", ".join(related_ids)
        prompt_snapshot = self._build_prompt_snapshot(feedback_items)
        body_markdown = self._build_markdown(primary_related_id, feedback_items)
        return self.draft_repository.create_draft(
            batch_id=batch_id,
            title=title,
            body_markdown=body_markdown,
            related_id_summary=related_id_summary,
            ai_model="deterministic-template-v1",
            prompt_snapshot=prompt_snapshot,
        )

    def _build_prompt_snapshot(self, feedback_items: list[FeedbackRecord]) -> str:
        lines = []
        for item in feedback_items:
            lines.append(f"- {item.type} | {item.related_id} | {item.raw_content}")
        return "\n".join(lines)

    def _build_markdown(self, primary_related_id: str, feedback_items: list[FeedbackRecord]) -> str:
        summary_lines = [f"- {item.raw_content}" for item in feedback_items]
        background_lines = [f"- {item.type}: {item.raw_content}" for item in feedback_items]
        steps_lines = []
        expected_lines = []
        actual_lines = []
        missing_lines = []

        for index, item in enumerate(feedback_items, start=1):
            if item.expected_behavior and item.actual_behavior:
                steps_lines.append(f"{index}. Review feedback item {item.id} and reproduce the reported flow.")
            if item.expected_behavior:
                expected_lines.append(f"- {item.expected_behavior}")
            else:
                missing_lines.append(f"- Missing expected behavior for feedback item {item.id}")
            if item.actual_behavior:
                actual_lines.append(f"- {item.actual_behavior}")
            else:
                missing_lines.append(f"- Missing actual behavior for feedback item {item.id}")

        if not steps_lines:
            steps_lines.append("1. Reproduction steps were not provided in the collected feedback.")
            missing_lines.append("- Missing reproducible steps across the selected feedback items")
        if not expected_lines:
            expected_lines.append("- Expected behavior details were not provided.")
        if not actual_lines:
            actual_lines.append("- Actual behavior details were not provided.")
        if not missing_lines:
            missing_lines.append("- No major missing information identified from the selected feedback items.")

        return "\n\n".join(
            [
                "Summary\n" + "\n".join(summary_lines),
                f"Related ID\n{primary_related_id}",
                f"User Signals Count\n{len(feedback_items)}",
                "Background\n" + "\n".join(background_lines),
                "Steps to Reproduce\n" + "\n".join(steps_lines),
                "Expected Behavior\n" + "\n".join(expected_lines),
                "Actual Behavior\n" + "\n".join(actual_lines),
                "Impact\n- Multiple users reported friction around this workflow.",
                "Missing Information\n" + "\n".join(missing_lines),
            ]
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
                "SELECT id, batch_id, title, body_markdown, related_id_summary, status, ai_model, prompt_snapshot, updated_at FROM drafts WHERE id = ?",
                (draft_id,),
            ).fetchone()
        return DraftRecord(**dict(row)) if row else None

    def get_draft_by_batch_id(self, batch_id: str) -> DraftRecord | None:
        with connection_context() as connection:
            row = connection.execute(
                "SELECT id, batch_id, title, body_markdown, related_id_summary, status, ai_model, prompt_snapshot, updated_at FROM drafts WHERE batch_id = ? ORDER BY updated_at DESC LIMIT 1",
                (batch_id,),
            ).fetchone()
        return DraftRecord(**dict(row)) if row else None

    def update_draft(self, draft_id: str, payload: DraftUpdatePayload) -> DraftRecord | None:
        updated_at = utc_now_iso()
        with connection_context() as connection:
            connection.execute(
                "UPDATE drafts SET title = ?, body_markdown = ?, updated_at = ? WHERE id = ?",
                (payload.title, payload.body_markdown, updated_at, draft_id),
            )
        return self.get_draft(draft_id)

    def update_draft_status(self, draft_id: str, status: DraftStatus) -> DraftRecord | None:
        updated_at = utc_now_iso()
        with connection_context() as connection:
            connection.execute(
                "UPDATE drafts SET status = ?, updated_at = ? WHERE id = ?",
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
            conditions.append("submissions.related_id = ?")
            params.append(related_id)
        if issue_type:
            conditions.append("feedback_items.type = ?")
            params.append(issue_type)
        if keyword:
            like_value = f"%{keyword.strip()}%"
            conditions.append("(drafts.title LIKE ? OR drafts.body_markdown LIKE ? OR submissions.related_id LIKE ?)")
            params.extend([like_value, like_value, like_value])

        conditions.append("submissions.response_status >= 200 AND submissions.response_status < 300")
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        offset = (page - 1) * page_size

        with connection_context() as connection:
            total = connection.execute(
                f"""
                SELECT COUNT(*) AS total
                FROM submissions
                JOIN drafts ON drafts.id = submissions.draft_id
                LEFT JOIN draft_batches ON draft_batches.id = drafts.batch_id
                LEFT JOIN draft_batch_items ON draft_batch_items.batch_id = draft_batches.id
                LEFT JOIN feedback_items ON feedback_items.id = draft_batch_items.feedback_item_id
                {where_clause}
                """,
                params,
            ).fetchone()["total"]

            rows = connection.execute(
                f"""
                SELECT DISTINCT
                    submissions.github_issue_number AS issue_number,
                    drafts.title AS title,
                    submissions.github_issue_url AS issue_url,
                    submissions.related_id AS related_id,
                    COALESCE(feedback_items.type, 'bug') AS type,
                    submissions.submitted_at AS submitted_at
                FROM submissions
                JOIN drafts ON drafts.id = submissions.draft_id
                LEFT JOIN draft_batches ON draft_batches.id = drafts.batch_id
                LEFT JOIN draft_batch_items ON draft_batch_items.batch_id = draft_batches.id
                LEFT JOIN feedback_items ON feedback_items.id = draft_batch_items.feedback_item_id
                {where_clause}
                ORDER BY submissions.submitted_at DESC
                LIMIT ? OFFSET ?
                """,
                [*params, page_size, offset],
            ).fetchall()

        return {
            "items": [dict(row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total": total,
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
                "INSERT OR IGNORE INTO draft_batches (id, status, primary_related_id, related_id_count, integration_error, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                ("batch_fixture", "submitted", related_id, 1, None, submitted_at, submitted_at),
            )
            connection.execute(
                "INSERT OR IGNORE INTO feedback_items (id, type, related_id, expected_behavior, actual_behavior, raw_content, status, created_at, submitted_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"fb_fixture_{issue_number}", issue_type, related_id, None, None, title, FeedbackStatus.SUBMITTED.value, submitted_at, submitted_at),
            )
            connection.execute(
                "INSERT OR IGNORE INTO draft_batch_items (id, batch_id, feedback_item_id) VALUES (?, ?, ?)",
                (f"dbi_{issue_number}", "batch_fixture", f"fb_fixture_{issue_number}"),
            )
            connection.execute(
                "INSERT OR REPLACE INTO drafts (id, batch_id, title, body_markdown, related_id_summary, status, ai_model, prompt_snapshot, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (draft_id, "batch_fixture", title, title, related_id, "submitted", None, None, submitted_at),
            )
            connection.execute(
                "INSERT OR REPLACE INTO submissions (id, draft_id, github_issue_number, github_issue_url, related_id, github_state, labels_snapshot, response_status, submitted_at, error_summary) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (f"sub_{issue_number}", draft_id, issue_number, issue_url, related_id, "open", None, 201, submitted_at, None),
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
        conditions = ["submitted_at >= ?", "response_status >= 200 AND response_status < 300"]
        params: list[object] = [since_iso]
        if related_id:
            conditions.append("related_id = ?")
            params.append(related_id)
        where_clause = f"WHERE {' AND '.join(conditions)}"
        with connection_context() as connection:
            row = connection.execute(
                f"SELECT COUNT(*) AS total FROM submissions {where_clause}",
                params,
            ).fetchone()
        return row["total"]


class GitHubSubmissionError(ValueError):
    pass


class GitHubIssueClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def create_issue(self, *, title: str, body: str) -> dict[str, object]:
        if not self.settings.github_token:
            raise GitHubSubmissionError("GITHUB_TOKEN is required")
        if not self.settings.github_repo_owner or not self.settings.github_repo_name:
            raise GitHubSubmissionError("GitHub repository settings are required")

        endpoint = (
            f"https://api.github.com/repos/{self.settings.github_repo_owner}/{self.settings.github_repo_name}/issues"
        )
        payload = json.dumps({"title": title, "body": body}).encode("utf-8")
        http_request = request.Request(
            endpoint,
            data=payload,
            method="POST",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.settings.github_token}",
                "Content-Type": "application/json",
                "User-Agent": "issue-aggregator-mvp",
            },
        )

        try:
            with request.urlopen(http_request, timeout=15) as response:
                response_body = json.loads(response.read().decode("utf-8"))
                return {
                    "issue_number": response_body["number"],
                    "issue_url": response_body["html_url"],
                    "related_id": response_body.get("body", ""),
                    "response_status": response.status,
                    "github_state": response_body.get("state"),
                }
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8") if exc.fp else str(exc)
            raise GitHubSubmissionError(detail or f"GitHub API request failed with status {exc.code}") from exc
        except error.URLError as exc:
            raise GitHubSubmissionError(str(exc.reason)) from exc


class DraftSubmissionService:
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
            raise RepositoryError("Draft not found")

        batch = self.batch_repository.get_batch(draft.batch_id)
        if not batch:
            raise RepositoryError("Draft batch not found")

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
                github_issue_url="",
                related_id=draft.related_id_summary,
                response_status=500,
                error_summary=str(exc),
            )
            raise RepositoryError(str(exc))

        feedback_items = self.batch_repository.list_batch_feedback_items(batch.id)
        self.feedback_repository.mark_feedback_submitted([item.id for item in feedback_items])
        self.draft_repository.update_draft_status(draft.id, DraftStatus.SUBMITTED)
        self.batch_repository.update_batch_status(batch.id, status=DraftBatchStatus.SUBMITTED)
        return self.submission_repository.create_submission(
            draft_id=draft.id,
            github_issue_number=int(github_response["issue_number"]),
            github_issue_url=str(github_response["issue_url"]),
            related_id=batch.primary_related_id or draft.related_id_summary,
            response_status=int(github_response["response_status"]),
            github_state=str(github_response.get("github_state") or "open"),
        )

    def _enforce_rate_limits(self, related_id_summary: str) -> None:
        now = datetime.now(timezone.utc)
        global_since = (now - timedelta(hours=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        total_recent = self.submission_repository.count_recent_submissions(since_iso=global_since)
        if total_recent >= self.settings.rate_limit_per_hour:
            raise RepositoryError("Submission rate limit reached")

        related_ids = [item.strip() for item in related_id_summary.split(",") if item.strip()]
        related_since = (now - timedelta(hours=self.settings.related_id_rate_limit_window)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        for related_id in related_ids:
            per_related_count = self.submission_repository.count_recent_submissions(
                related_id=related_id,
                since_iso=related_since,
            )
            if per_related_count > 0:
                raise RepositoryError(f"related_id rate limit reached for {related_id}")
