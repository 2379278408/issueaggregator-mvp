import os
import tempfile
import unittest
from dataclasses import replace

from fastapi import HTTPException
from pydantic import ValidationError


class ApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DATABASE_URL"] = f"sqlite:///{self.temp_dir.name}/test.db"

        from app.database import initialize_database
        from app.models import DraftBatchCreatePayload, DraftUpdatePayload, FeedbackCreatePayload
        from app.routers.feedback import (
            create_draft_batch,
            create_feedback,
            get_draft,
            integrate_draft_batch,
            list_feedback,
            list_submitted_issues,
            require_admin_token,
            search_submitted_issues,
            update_draft,
        )
        from app.repositories import SubmissionRepository
        from app.routers import feedback as feedback_router_module

        initialize_database()
        self.DraftBatchCreatePayload = DraftBatchCreatePayload
        self.DraftUpdatePayload = DraftUpdatePayload
        self.FeedbackCreatePayload = FeedbackCreatePayload
        self.create_draft_batch = create_draft_batch
        self.create_feedback = create_feedback
        self.get_draft = get_draft
        self.integrate_draft_batch = integrate_draft_batch
        self.list_feedback = list_feedback
        self.list_submitted_issues = list_submitted_issues
        self.require_admin_token = require_admin_token
        self.search_submitted_issues = search_submitted_issues
        self.update_draft = update_draft
        self.submission_repository = SubmissionRepository()
        self.feedback_router_module = feedback_router_module

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        os.environ.pop("DATABASE_URL", None)

    def test_admin_router_requires_token_dependency(self) -> None:
        self.assertTrue(self.feedback_router_module.admin_router.dependencies)

    def test_admin_token_dependency_rejects_missing_or_invalid_token(self) -> None:
        original_settings = self.feedback_router_module.settings
        self.feedback_router_module.settings = replace(original_settings, admin_api_token="secret-token")
        try:
            with self.assertRaises(HTTPException) as missing:
                self.require_admin_token(None)
            self.assertEqual(missing.exception.status_code, 401)

            with self.assertRaises(HTTPException) as invalid:
                self.require_admin_token("wrong-token")
            self.assertEqual(invalid.exception.status_code, 401)
        finally:
            self.feedback_router_module.settings = original_settings

    def test_admin_token_dependency_accepts_configured_token(self) -> None:
        original_settings = self.feedback_router_module.settings
        self.feedback_router_module.settings = replace(original_settings, admin_api_token="secret-token")
        try:
            self.assertIsNone(self.require_admin_token("secret-token"))
        finally:
            self.feedback_router_module.settings = original_settings

    def test_create_feedback_success(self) -> None:
        payload = self.FeedbackCreatePayload(
            type="bug",
            related_id="editor-copy-button",
            raw_content="复制按钮在暗色模式下不可见",
            expected_behavior="按钮可见",
            actual_behavior="按钮颜色过浅",
        )
        response = self.create_feedback(payload)

        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["status"], "pending")
        self.assertTrue(response["data"]["id"].startswith("fb_"))

    def test_create_feedback_rejects_invalid_related_id(self) -> None:
        with self.assertRaises(ValidationError):
            self.FeedbackCreatePayload(
                type="bug",
                related_id="Editor Copy Button",
                raw_content="内容",
            )

    def test_list_submitted_issues_descending(self) -> None:
        self.submission_repository.create_submission_fixture(
            draft_id="draft_1",
            issue_number=101,
            issue_url="https://github.com/org/repo/issues/101",
            related_id="editor-copy-button",
            submitted_at="2026-06-11T10:30:00Z",
            title="[Bug] Copy button invisible in dark mode",
            issue_type="bug",
        )
        self.submission_repository.create_submission_fixture(
            draft_id="draft_2",
            issue_number=102,
            issue_url="https://github.com/org/repo/issues/102",
            related_id="login-oauth-flow",
            submitted_at="2026-06-11T10:40:00Z",
            title="[Bug] Login callback fails",
            issue_type="bug",
        )

        response = self.list_submitted_issues()

        items = response["data"]["items"]
        self.assertEqual(items[0]["issue_number"], 102)
        self.assertEqual(items[1]["issue_number"], 101)

    def test_search_submitted_issues_by_related_id(self) -> None:
        self.submission_repository.create_submission_fixture(
            draft_id="draft_1",
            issue_number=201,
            issue_url="https://github.com/org/repo/issues/201",
            related_id="editor-copy-button",
            submitted_at="2026-06-11T10:30:00Z",
            title="[Bug] Copy button invisible in dark mode",
            issue_type="bug",
        )
        self.submission_repository.create_submission_fixture(
            draft_id="draft_2",
            issue_number=202,
            issue_url="https://github.com/org/repo/issues/202",
            related_id="settings-sync-error",
            submitted_at="2026-06-11T10:40:00Z",
            title="[Bug] Settings sync failed",
            issue_type="bug",
        )

        response = self.search_submitted_issues(related_id="editor-copy-button")

        items = response["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["related_id"], "editor-copy-button")

    def test_list_feedback_by_pending_status(self) -> None:
        self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item")
        )
        self.create_feedback(
            self.FeedbackCreatePayload(type="feature", related_id="login-oauth-flow", raw_content="second item")
        )

        response = self.list_feedback(status="pending")

        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["total"], 2)
        self.assertEqual(response["data"]["items"][0]["status"], "pending")

    def test_create_draft_batch_success(self) -> None:
        first = self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item")
        )
        second = self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="second item")
        )

        response = self.create_draft_batch(
            self.DraftBatchCreatePayload(
                feedback_item_ids=[first["data"]["id"], second["data"]["id"]],
                confirm_mixed_related_ids=False,
            )
        )

        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["status"], "created")
        self.assertEqual(response["data"]["primary_related_id"], "editor-copy-button")
        self.assertEqual(response["data"]["related_id_count"], 1)

    def test_create_draft_batch_requires_mixed_related_id_confirmation(self) -> None:
        first = self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item")
        )
        second = self.create_feedback(
            self.FeedbackCreatePayload(type="feature", related_id="login-oauth-flow", raw_content="second item")
        )

        response = self.create_draft_batch(
            self.DraftBatchCreatePayload(
                feedback_item_ids=[first["data"]["id"], second["data"]["id"]],
                confirm_mixed_related_ids=False,
            )
        )

        self.assertFalse(response["success"])
        self.assertEqual(response["error_code"], "MIXED_RELATED_ID_CONFIRM_REQUIRED")

    def test_create_draft_batch_marks_feedback_as_grouped(self) -> None:
        first = self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item")
        )

        self.create_draft_batch(
            self.DraftBatchCreatePayload(
                feedback_item_ids=[first["data"]["id"]],
                confirm_mixed_related_ids=False,
            )
        )

        grouped_response = self.list_feedback(status="grouped")
        self.assertEqual(grouped_response["data"]["total"], 1)
        self.assertEqual(grouped_response["data"]["items"][0]["id"], first["data"]["id"])

    def test_integrate_batch_returns_draft(self) -> None:
        first = self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item")
        )
        batch = self.create_draft_batch(
            self.DraftBatchCreatePayload(
                feedback_item_ids=[first["data"]["id"]],
                confirm_mixed_related_ids=False,
            )
        )

        response = self.integrate_draft_batch(batch["data"]["id"])

        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["status"], "draft_ready")

    def test_get_and_update_draft(self) -> None:
        first = self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item")
        )
        batch = self.create_draft_batch(
            self.DraftBatchCreatePayload(
                feedback_item_ids=[first["data"]["id"]],
                confirm_mixed_related_ids=False,
            )
        )
        integrate_response = self.integrate_draft_batch(batch["data"]["id"])
        draft_id = integrate_response["data"]["draft_id"]

        draft_response = self.get_draft(draft_id)
        update_response = self.update_draft(
            draft_id,
            self.DraftUpdatePayload(title="Updated title", body_markdown="Updated body"),
        )

        self.assertTrue(draft_response["success"])
        self.assertEqual(draft_response["data"]["id"], draft_id)
        self.assertTrue(update_response["success"])
        self.assertEqual(update_response["data"]["id"], draft_id)

    def test_submit_draft_returns_submission_payload(self) -> None:
        first = self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item")
        )
        batch = self.create_draft_batch(
            self.DraftBatchCreatePayload(
                feedback_item_ids=[first["data"]["id"]],
                confirm_mixed_related_ids=False,
            )
        )
        integrate_response = self.integrate_draft_batch(batch["data"]["id"])
        draft_id = integrate_response["data"]["draft_id"]

        class FakeSubmissionService:
            def submit_draft(self, _: str):
                from app.models import SubmissionRecord

                return SubmissionRecord(
                    id="sub_1",
                    draft_id=draft_id,
                    github_issue_number=501,
                    github_issue_url="https://github.com/org/repo/issues/501",
                    related_id="editor-copy-button",
                    github_state="open",
                    labels_snapshot=None,
                    response_status=201,
                    submitted_at="2026-06-11T11:20:00Z",
                    error_summary=None,
                )

        original_service = self.feedback_router_module.draft_submission_service
        self.feedback_router_module.draft_submission_service = FakeSubmissionService()
        try:
            response = self.feedback_router_module.submit_draft(draft_id)
        finally:
            self.feedback_router_module.draft_submission_service = original_service

        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["issue_number"], 501)

    def test_submit_draft_returns_token_missing(self) -> None:
        class MissingTokenSubmissionService:
            def submit_draft(self, _: str):
                from app.repositories import RepositoryError

                raise RepositoryError("GITHUB_TOKEN is required")

        original_service = self.feedback_router_module.draft_submission_service
        self.feedback_router_module.draft_submission_service = MissingTokenSubmissionService()
        try:
            response = self.feedback_router_module.submit_draft("draft_1234567890ab")
        finally:
            self.feedback_router_module.draft_submission_service = original_service

        self.assertFalse(response["success"])
        self.assertEqual(response["error_code"], "TOKEN_MISSING")


if __name__ == "__main__":
    unittest.main()
