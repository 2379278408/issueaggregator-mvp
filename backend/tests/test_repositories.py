import os
import tempfile
import unittest

from pydantic import ValidationError

os.environ["APP_ENV"] = "test"


class RepositoryModelTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["APP_ENV"] = "test"
        os.environ["DATABASE_URL"] = f"sqlite:///{self.temp_dir.name}/test.db"

        from app.database import initialize_database
        from app.models import DraftStatus, DraftUpdatePayload, FeedbackCreatePayload, FeedbackStatus
        from app.repositories import (
            DraftBatchRepository,
            DraftBatchService,
            DraftIntegrationService,
            DraftRepository,
            DraftSubmissionService,
            FeedbackRepository,
            GitHubSubmissionError,
            RepositoryError,
            SubmissionRepository,
        )

        initialize_database()
        self.DraftStatus = DraftStatus
        self.DraftUpdatePayload = DraftUpdatePayload
        self.FeedbackCreatePayload = FeedbackCreatePayload
        self.FeedbackStatus = FeedbackStatus
        self.DraftBatchRepository = DraftBatchRepository
        self.DraftBatchService = DraftBatchService
        self.DraftIntegrationService = DraftIntegrationService
        self.DraftRepository = DraftRepository
        self.DraftSubmissionService = DraftSubmissionService
        self.FeedbackRepository = FeedbackRepository
        self.GitHubSubmissionError = GitHubSubmissionError
        self.RepositoryError = RepositoryError
        self.SubmissionRepository = SubmissionRepository

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        os.environ.pop("APP_ENV", None)
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("AI_API_KEY", None)
        os.environ.pop("AI_API_BASE_URL", None)
        os.environ.pop("AI_MODEL", None)
        os.environ.pop("GITHUB_TOKEN", None)
        os.environ.pop("GITHUB_REPO_OWNER", None)
        os.environ.pop("GITHUB_REPO_NAME", None)

    def test_related_id_accepts_slug_format(self) -> None:
        payload = self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="valid content")
        self.assertEqual(payload.related_id, "editor-copy-button")

    def test_related_id_rejects_invalid_format(self) -> None:
        with self.assertRaises(ValidationError):
            self.FeedbackCreatePayload(type="bug", related_id="Editor Copy Button", raw_content="invalid")

    def test_feedback_payload_rejects_overlong_content(self) -> None:
        with self.assertRaises(ValidationError):
            self.FeedbackCreatePayload(
                type="bug",
                related_id="editor-copy-button",
                raw_content="x" * 2001,
            )

    def test_draft_batch_payload_rejects_duplicate_feedback_ids(self) -> None:
        from app.models import DraftBatchCreatePayload

        with self.assertRaises(ValidationError):
            DraftBatchCreatePayload(
                feedback_item_ids=["fb_1234567890ab", "fb_1234567890ab"],
                confirm_mixed_related_ids=False,
            )

    def test_feedback_status_transition_updates_rows(self) -> None:
        repository = self.FeedbackRepository()
        first = repository.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item")
        )
        second = repository.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="second item")
        )

        updated = repository.update_feedback_status([first.id, second.id], self.FeedbackStatus.GROUPED)
        grouped_items = repository.list_feedback(status=self.FeedbackStatus.GROUPED)

        self.assertEqual(updated, 2)
        self.assertEqual(grouped_items["total"], 2)
        self.assertEqual(grouped_items["items"][0]["status"], self.FeedbackStatus.GROUPED.value)

    def test_feedback_item_has_unique_active_batch_ownership(self) -> None:
        feedback_repository = self.FeedbackRepository()
        batch_repository = self.DraftBatchRepository()

        feedback = feedback_repository.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item")
        )
        first_batch = batch_repository.create_batch(primary_related_id=feedback.related_id, related_id_count=1)
        second_batch = batch_repository.create_batch(primary_related_id=feedback.related_id, related_id_count=1)

        batch_repository.attach_feedback_items(first_batch.id, [feedback.id])

        with self.assertRaises(self.RepositoryError):
            batch_repository.attach_feedback_items(second_batch.id, [feedback.id])

    def test_create_and_get_draft_record(self) -> None:
        batch_repository = self.DraftBatchRepository()
        draft_repository = self.DraftRepository()

        batch = batch_repository.create_batch(primary_related_id="editor-copy-button", related_id_count=1)
        draft = draft_repository.create_draft(
            batch_id=batch.id,
            title="[Bug] Copy button invisible in dark mode",
            body_markdown="Summary\n\nRelated ID",
            related_id_summary="editor-copy-button",
            status=self.DraftStatus.DRAFT_READY,
        )
        stored = draft_repository.get_draft(draft.id)

        self.assertIsNotNone(stored)
        self.assertEqual(stored.title, draft.title)
        self.assertEqual(stored.status, self.DraftStatus.DRAFT_READY)

    def test_create_submission_record(self) -> None:
        batch_repository = self.DraftBatchRepository()
        draft_repository = self.DraftRepository()
        submission_repository = self.SubmissionRepository()

        batch = batch_repository.create_batch(primary_related_id="editor-copy-button", related_id_count=1)
        draft = draft_repository.create_draft(
            batch_id=batch.id,
            title="[Bug] Copy button invisible in dark mode",
            body_markdown="Summary\n\nRelated ID",
            related_id_summary="editor-copy-button",
        )
        submission = submission_repository.create_submission(
            draft_id=draft.id,
            github_issue_number=101,
            github_issue_url="https://github.com/org/repo/issues/101",
            related_id="editor-copy-button",
            response_status=201,
        )

        self.assertEqual(submission.github_issue_number, 101)
        self.assertEqual(submission.related_id, "editor-copy-button")

    def test_draft_batch_service_requires_explicit_confirmation_for_mixed_related_ids(self) -> None:
        feedback_repository = self.FeedbackRepository()
        service = self.DraftBatchService()

        first = feedback_repository.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item")
        )
        second = feedback_repository.create_feedback(
            self.FeedbackCreatePayload(type="feature", related_id="login-oauth-flow", raw_content="second item")
        )

        with self.assertRaises(self.RepositoryError):
            service.create_batch([first.id, second.id], confirm_mixed_related_ids=False)

    def test_integrate_batch_generates_placeholder_sections(self) -> None:
        feedback_repository = self.FeedbackRepository()
        batch_service = self.DraftBatchService()
        integration_service = self.DraftIntegrationService()

        first = feedback_repository.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="copy button is invisible")
        )
        batch = batch_service.create_batch([first.id], confirm_mixed_related_ids=False)

        draft = integration_service.integrate_batch(batch.id)

        self.assertEqual(draft.status, self.DraftStatus.DRAFT_READY)
        self.assertIn("Missing Information", draft.body_markdown)
        self.assertIn("Missing expected behavior", draft.body_markdown)

    def test_update_draft_persists_new_content(self) -> None:
        batch_repository = self.DraftBatchRepository()
        draft_repository = self.DraftRepository()

        batch = batch_repository.create_batch(primary_related_id="editor-copy-button", related_id_count=1)
        draft = draft_repository.create_draft(
            batch_id=batch.id,
            title="Old title",
            body_markdown="Old body",
            related_id_summary="editor-copy-button",
        )

        updated = draft_repository.update_draft(
            draft.id,
            self.DraftUpdatePayload(title="New title", body_markdown="New body"),
        )

        self.assertIsNotNone(updated)
        self.assertEqual(updated.title, "New title")
        self.assertEqual(updated.body_markdown, "New body")

    def test_submit_draft_updates_linked_statuses(self) -> None:
        os.environ["GITHUB_TOKEN"] = "test-token"
        os.environ["GITHUB_REPO_OWNER"] = "org"
        os.environ["GITHUB_REPO_NAME"] = "repo"

        feedback_repository = self.FeedbackRepository()
        batch_service = self.DraftBatchService()
        integration_service = self.DraftIntegrationService()
        submission_service = self.DraftSubmissionService()

        first = feedback_repository.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="copy button is invisible")
        )
        batch = batch_service.create_batch([first.id], confirm_mixed_related_ids=False)
        draft = integration_service.integrate_batch(batch.id)

        class FakeGitHubClient:
            def create_issue(self, *, title: str, body: str) -> dict[str, object]:
                return {
                    "issue_number": 301,
                    "issue_url": "https://github.com/org/repo/issues/301",
                    "response_status": 201,
                    "github_state": "open",
                }

        submission_service.github_client = FakeGitHubClient()
        submission = submission_service.submit_draft(draft.id)
        submitted_items = feedback_repository.list_feedback(status=self.FeedbackStatus.SUBMITTED)

        self.assertEqual(submission.github_issue_number, 301)
        self.assertEqual(submitted_items["total"], 1)

    def test_integrate_batch_uses_ai_when_configured(self) -> None:
        os.environ["AI_API_KEY"] = "test-ai-token"
        os.environ["AI_API_BASE_URL"] = "https://example.test/v1"
        os.environ["AI_MODEL"] = "test-model"

        feedback_repository = self.FeedbackRepository()
        batch_service = self.DraftBatchService()
        integration_service = self.DraftIntegrationService()

        class FakeAIClient:
            def create_issue_draft(self, *, prompt_snapshot: str, feedback_items: list[object]) -> dict[str, str]:
                return {
                    "title": "AI generated issue",
                    "body_markdown": f"AI body from {len(feedback_items)} feedback item",
                }

        integration_service.ai_client = FakeAIClient()
        first = feedback_repository.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="copy button is invisible")
        )
        batch = batch_service.create_batch([first.id], confirm_mixed_related_ids=False)

        draft = integration_service.integrate_batch(batch.id)

        self.assertEqual(draft.title, "AI generated issue")
        self.assertEqual(draft.body_markdown, "AI body from 1 feedback item")
        self.assertEqual(draft.ai_model, "test-model")

    def test_integrate_batch_marks_failed_when_ai_fails(self) -> None:
        os.environ["AI_API_KEY"] = "test-ai-token"
        os.environ["AI_API_BASE_URL"] = "https://example.test/v1"
        os.environ["AI_MODEL"] = "test-model"

        from app.repositories import AIIntegrationError

        feedback_repository = self.FeedbackRepository()
        batch_repository = self.DraftBatchRepository()
        batch_service = self.DraftBatchService()
        integration_service = self.DraftIntegrationService()

        class FailingAIClient:
            def create_issue_draft(self, *, prompt_snapshot: str, feedback_items: list[object]) -> dict[str, str]:
                raise AIIntegrationError("AI unavailable")

        integration_service.ai_client = FailingAIClient()
        first = feedback_repository.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="copy button is invisible")
        )
        batch = batch_service.create_batch([first.id], confirm_mixed_related_ids=False)

        with self.assertRaises(self.RepositoryError):
            integration_service.integrate_batch(batch.id)

        stored_batch = batch_repository.get_batch(batch.id)
        self.assertEqual(stored_batch.status.value, "failed")
        self.assertEqual(stored_batch.integration_error, "AI unavailable")

    def test_submit_draft_enforces_related_id_rate_limit(self) -> None:
        os.environ["GITHUB_TOKEN"] = "test-token"
        os.environ["GITHUB_REPO_OWNER"] = "org"
        os.environ["GITHUB_REPO_NAME"] = "repo"

        submission_repository = self.SubmissionRepository()
        submission_repository.create_submission_fixture(
            draft_id="draft_existing",
            issue_number=401,
            issue_url="https://github.com/org/repo/issues/401",
            related_id="editor-copy-button",
            submitted_at="2026-06-11T10:30:00Z",
            title="Existing issue",
            issue_type="bug",
        )

        feedback_repository = self.FeedbackRepository()
        batch_service = self.DraftBatchService()
        integration_service = self.DraftIntegrationService()
        submission_service = self.DraftSubmissionService()
        first = feedback_repository.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="copy button is invisible")
        )
        batch = batch_service.create_batch([first.id], confirm_mixed_related_ids=False)
        draft = integration_service.integrate_batch(batch.id)

        with self.assertRaises(self.RepositoryError):
            submission_service.submit_draft(draft.id)

    def test_submit_draft_marks_failure_when_github_call_fails(self) -> None:
        os.environ["GITHUB_TOKEN"] = "test-token"
        os.environ["GITHUB_REPO_OWNER"] = "org"
        os.environ["GITHUB_REPO_NAME"] = "repo"

        feedback_repository = self.FeedbackRepository()
        batch_service = self.DraftBatchService()
        integration_service = self.DraftIntegrationService()
        submission_service = self.DraftSubmissionService()

        first = feedback_repository.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="copy button is invisible")
        )
        batch = batch_service.create_batch([first.id], confirm_mixed_related_ids=False)
        draft = integration_service.integrate_batch(batch.id)

        class FailingGitHubClient:
            def create_issue(self, *, title: str, body: str) -> dict[str, object]:
                raise self.GitHubSubmissionError("bad gateway")

            def __init__(self, error_cls):
                self.GitHubSubmissionError = error_cls

        submission_service.github_client = FailingGitHubClient(self.GitHubSubmissionError)

        with self.assertRaises(self.RepositoryError):
            submission_service.submit_draft(draft.id)

        stored_draft = submission_service.draft_repository.get_draft(draft.id)
        self.assertEqual(stored_draft.status, self.DraftStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
