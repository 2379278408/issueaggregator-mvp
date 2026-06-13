import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor

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
            AuditEventRepository,
            DraftBatchRepository,
            DraftBatchService,
            DraftIntegrationService,
            DraftRepository,
            DraftSubmissionService,
            FeedbackRepository,
            GitHubSubmissionError,
            PublicFeedbackRateLimitRepository,
            RepositoryError,
            SubmissionRepository,
        )

        initialize_database()
        self.DraftStatus = DraftStatus
        self.DraftUpdatePayload = DraftUpdatePayload
        self.FeedbackCreatePayload = FeedbackCreatePayload
        self.FeedbackStatus = FeedbackStatus
        self.AuditEventRepository = AuditEventRepository
        self.DraftBatchRepository = DraftBatchRepository
        self.DraftBatchService = DraftBatchService
        self.DraftIntegrationService = DraftIntegrationService
        self.DraftRepository = DraftRepository
        self.DraftSubmissionService = DraftSubmissionService
        self.FeedbackRepository = FeedbackRepository
        self.GitHubSubmissionError = GitHubSubmissionError
        self.PublicFeedbackRateLimitRepository = PublicFeedbackRateLimitRepository
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

    def test_feedback_repository_counts_recent_duplicate_feedback(self) -> None:
        repository = self.FeedbackRepository()
        payload = self.FeedbackCreatePayload(
            type="bug",
            related_id="editor-copy-button",
            raw_content="first item",
            expected_behavior="visible",
            actual_behavior="hidden",
        )
        repository.create_feedback(payload)

        duplicate_count = repository.count_recent_duplicate_feedback(
            payload,
            since_iso="2026-01-01T00:00:00Z",
        )

        self.assertEqual(duplicate_count, 1)

    def test_audit_event_repository_counts_recent_events(self) -> None:
        repository = self.AuditEventRepository()
        repository.create_event(
            event_id="audit_001",
            event_type="admin_auth_failed",
            client_ip="8.8.8.8",
            path="/api/admin/workbench/feedback",
            action=None,
            resource_id=None,
        )

        count = repository.count_recent_events(
            event_type="admin_auth_failed",
            client_ip="8.8.8.8",
            since_iso="2026-01-01T00:00:00Z",
        )

        self.assertEqual(count, 1)

    def test_audit_event_repository_lists_recent_events(self) -> None:
        repository = self.AuditEventRepository()
        repository.create_event(
            event_id="audit_001",
            event_type="admin_auth_failed",
            client_ip="8.8.8.8",
            path="/api/admin/workbench/feedback",
        )
        repository.create_event(
            event_id="audit_002",
            event_type="admin_action_succeeded",
            client_ip="8.8.4.4",
            path="/api/admin/workbench/draft-batches",
            action="create_draft_batch",
            resource_id="batch_123",
        )

        events = repository.list_events(page=1, page_size=10)
        filtered = repository.list_events(event_type="admin_action_succeeded", page=1, page_size=10)

        self.assertEqual(events["total"], 2)
        self.assertEqual(events["items"][0]["id"], "audit_002")
        self.assertEqual(filtered["total"], 1)
        self.assertEqual(filtered["items"][0]["action"], "create_draft_batch")

    def test_audit_event_repository_filters_by_keyword(self) -> None:
        repository = self.AuditEventRepository()
        repository.create_event(
            event_id="audit_001",
            event_type="admin_auth_failed",
            client_ip="8.8.8.8",
            path="/api/admin/workbench/feedback",
        )
        repository.create_event(
            event_id="audit_002",
            event_type="admin_action_succeeded",
            client_ip="8.8.4.4",
            path="/api/admin/workbench/draft-batches",
            action="create_draft_batch",
            resource_id="batch_123",
        )

        filtered = repository.list_events(keyword="batch_123", page=1, page_size=10)

        self.assertEqual(filtered["total"], 1)
        self.assertEqual(filtered["items"][0]["id"], "audit_002")

    def test_audit_event_repository_filters_by_since_iso(self) -> None:
        repository = self.AuditEventRepository()
        repository.create_event(
            event_id="audit_001",
            event_type="admin_auth_failed",
            client_ip="8.8.8.8",
            path="/api/admin/workbench/feedback",
        )

        future_window = repository.list_events(since_iso="2999-01-01T00:00:00Z", page=1, page_size=10)
        current_window = repository.list_events(since_iso="2026-01-01T00:00:00Z", page=1, page_size=10)

        self.assertEqual(future_window["total"], 0)
        self.assertEqual(current_window["total"], 1)

    def test_audit_event_repository_keyword_matches_action_and_client_ip(self) -> None:
        repository = self.AuditEventRepository()
        repository.create_event(
            event_id="audit_001",
            event_type="admin_auth_failed",
            client_ip="1.1.1.1",
            path="/api/admin/workbench/feedback",
        )
        repository.create_event(
            event_id="audit_002",
            event_type="admin_action_succeeded",
            client_ip="9.9.9.9",
            path="/api/admin/workbench/draft-batches",
            action="submit_draft",
            resource_id="draft_123",
        )

        by_action = repository.list_events(keyword="submit_draft", page=1, page_size=10)
        by_client_ip = repository.list_events(keyword="9.9.9.9", page=1, page_size=10)

        self.assertEqual(by_action["total"], 1)
        self.assertEqual(by_action["items"][0]["id"], "audit_002")
        self.assertEqual(by_client_ip["total"], 1)
        self.assertEqual(by_client_ip["items"][0]["id"], "audit_002")

    def test_audit_event_repository_paginates_descending_results(self) -> None:
        repository = self.AuditEventRepository()
        repository.create_event(
            event_id="audit_001",
            event_type="admin_auth_failed",
            client_ip="8.8.8.8",
            path="/api/admin/workbench/feedback",
        )
        repository.create_event(
            event_id="audit_002",
            event_type="admin_action_succeeded",
            client_ip="8.8.4.4",
            path="/api/admin/workbench/draft-batches",
            action="create_draft_batch",
            resource_id="batch_123",
        )

        first_page = repository.list_events(page=1, page_size=1)
        second_page = repository.list_events(page=2, page_size=1)

        self.assertEqual(first_page["total"], 2)
        self.assertEqual(len(first_page["items"]), 1)
        self.assertEqual(first_page["items"][0]["id"], "audit_002")
        self.assertEqual(second_page["total"], 2)
        self.assertEqual(len(second_page["items"]), 1)
        self.assertEqual(second_page["items"][0]["id"], "audit_001")

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

    def test_public_feedback_rate_limit_consumes_quota_atomically(self) -> None:
        repository = self.PublicFeedbackRateLimitRepository()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    lambda _: repository.consume_daily_quota(ip_address="203.0.113.10", limit=1),
                    range(2),
                )
            )

        self.assertEqual(results.count(True), 1)
        self.assertEqual(results.count(False), 1)

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
        self.assertIn("## 待补充信息", draft.body_markdown)
        self.assertIn("缺少期望表现", draft.body_markdown)
        self.assertIn("## 原始反馈", draft.body_markdown)

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

    def test_list_submitted_issues_deduplicates_grouped_feedback(self) -> None:
        os.environ["GITHUB_TOKEN"] = "test-token"
        os.environ["GITHUB_REPO_OWNER"] = "org"
        os.environ["GITHUB_REPO_NAME"] = "repo"

        feedback_repository = self.FeedbackRepository()
        batch_service = self.DraftBatchService()
        integration_service = self.DraftIntegrationService()
        submission_service = self.DraftSubmissionService()
        first = feedback_repository.create_feedback(
            self.FeedbackCreatePayload(type="feature", related_id="push-email", raw_content="first item")
        )
        second = feedback_repository.create_feedback(
            self.FeedbackCreatePayload(type="enhancement", related_id="push-email", raw_content="second item")
        )
        batch = batch_service.create_batch([first.id, second.id], confirm_mixed_related_ids=False)
        draft = integration_service.integrate_batch(batch.id)

        class FakeGitHubClient:
            def create_issue(self, *, title: str, body: str) -> dict[str, object]:
                return {
                    "issue_number": 302,
                    "issue_url": "https://github.com/org/repo/issues/302",
                    "response_status": 201,
                    "github_state": "open",
                }

        submission_service.github_client = FakeGitHubClient()
        submission_service.submit_draft(draft.id)

        submitted = self.SubmissionRepository().list_submitted_issues(page=1, page_size=20)

        self.assertEqual(submitted["total"], 1)
        self.assertEqual(len(submitted["items"]), 1)
        self.assertEqual(submitted["items"][0]["issue_number"], 302)
        self.assertEqual(submitted["items"][0]["type"], "mixed")

    def test_list_submitted_issues_returns_filtered_type_when_searching_by_type(self) -> None:
        os.environ["GITHUB_TOKEN"] = "test-token"
        os.environ["GITHUB_REPO_OWNER"] = "org"
        os.environ["GITHUB_REPO_NAME"] = "repo"

        feedback_repository = self.FeedbackRepository()
        batch_service = self.DraftBatchService()
        integration_service = self.DraftIntegrationService()
        submission_service = self.DraftSubmissionService()
        first = feedback_repository.create_feedback(
            self.FeedbackCreatePayload(type="feature", related_id="push-email", raw_content="first item")
        )
        second = feedback_repository.create_feedback(
            self.FeedbackCreatePayload(type="enhancement", related_id="push-email", raw_content="second item")
        )
        batch = batch_service.create_batch([first.id, second.id], confirm_mixed_related_ids=False)
        draft = integration_service.integrate_batch(batch.id)

        class FakeGitHubClient:
            def create_issue(self, *, title: str, body: str) -> dict[str, object]:
                return {
                    "issue_number": 303,
                    "issue_url": "https://github.com/org/repo/issues/303",
                    "response_status": 201,
                    "github_state": "open",
                }

        submission_service.github_client = FakeGitHubClient()
        submission_service.submit_draft(draft.id)

        submitted = self.SubmissionRepository().list_submitted_issues(page=1, page_size=20, issue_type="feature")

        self.assertEqual(submitted["total"], 1)
        self.assertEqual(submitted["items"][0]["type"], "feature")

    def test_integrate_batch_uses_ai_when_configured(self) -> None:
        os.environ["AI_API_KEY"] = "test-ai-token"
        os.environ["AI_API_BASE_URL"] = "https://example.test/v1"
        os.environ["AI_MODEL"] = "test-model"

        feedback_repository = self.FeedbackRepository()
        batch_service = self.DraftBatchService()
        integration_service = self.DraftIntegrationService()

        class FakeAIClient:
            prompt_snapshot = ""

            def create_issue_draft(self, *, prompt_snapshot: str, feedback_items: list[object]) -> dict[str, str]:
                self.prompt_snapshot = prompt_snapshot
                return {
                    "title": "[缺陷] 复制按钮不可见",
                    "body_markdown": f"## 摘要\nAI 整理了 {len(feedback_items)} 条反馈",
                }

        fake_ai_client = FakeAIClient()
        integration_service.ai_client = fake_ai_client
        first = feedback_repository.create_feedback(
            self.FeedbackCreatePayload(
                type="bug",
                related_id="editor-copy-button",
                raw_content="copy button is invisible",
                expected_behavior="button should be visible",
                actual_behavior="button blends into the background",
            )
        )
        batch = batch_service.create_batch([first.id], confirm_mixed_related_ids=False)

        draft = integration_service.integrate_batch(batch.id)

        self.assertEqual(draft.title, "[缺陷] 复制按钮不可见")
        self.assertEqual(draft.body_markdown, "## 摘要\nAI 整理了 1 条反馈")
        self.assertEqual(draft.ai_model, "test-model")
        self.assertIn("类型: 缺陷", fake_ai_client.prompt_snapshot)
        self.assertIn("期望表现: button should be visible", fake_ai_client.prompt_snapshot)
        self.assertIn("实际表现: button blends into the background", fake_ai_client.prompt_snapshot)

    def test_integrate_batch_falls_back_when_ai_fails(self) -> None:
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

        draft = integration_service.integrate_batch(batch.id)

        stored_batch = batch_repository.get_batch(batch.id)
        self.assertEqual(stored_batch.status.value, "draft_ready")
        self.assertEqual(draft.ai_model, "deterministic-template-v1")
        self.assertIn("## 待补充信息", draft.body_markdown)

    def test_openai_client_rejects_non_chinese_issue_template(self) -> None:
        from app.repositories import AIIntegrationError, OpenAICompatibleClient

        client = OpenAICompatibleClient()

        with self.assertRaises(AIIntegrationError):
            client._validate_issue_draft(
                title="Test Callback Response Accuracy Between Front-End and Back-End",
                body_markdown="## Summary\nEnglish output without required Chinese sections",
            )

    def test_integrate_batch_falls_back_when_ai_returns_template_validation_error(self) -> None:
        os.environ["AI_API_KEY"] = "test-ai-token"
        os.environ["AI_API_BASE_URL"] = "https://example.test/v1"
        os.environ["AI_MODEL"] = "test-model"

        from app.repositories import AIIntegrationError

        feedback_repository = self.FeedbackRepository()
        batch_repository = self.DraftBatchRepository()
        batch_service = self.DraftBatchService()
        integration_service = self.DraftIntegrationService()

        class InvalidAIClient:
            def create_issue_draft(self, *, prompt_snapshot: str, feedback_items: list[object]) -> dict[str, str]:
                raise AIIntegrationError("AI response title did not follow the required Chinese format")

        integration_service.ai_client = InvalidAIClient()
        first = feedback_repository.create_feedback(
            self.FeedbackCreatePayload(type="question", related_id="test-callbcak", raw_content="测试前后端是否正确响应")
        )
        batch = batch_service.create_batch([first.id], confirm_mixed_related_ids=False)

        draft = integration_service.integrate_batch(batch.id)

        stored_batch = batch_repository.get_batch(batch.id)
        self.assertEqual(stored_batch.status.value, "draft_ready")
        self.assertEqual(draft.ai_model, "deterministic-template-v1")
        self.assertTrue(draft.title.startswith("[问题]"))
        self.assertIn("## 摘要", draft.body_markdown)
        self.assertIn("## 原始反馈", draft.body_markdown)

    def test_ai_user_prompt_requires_chinese_github_issue(self) -> None:
        from app.repositories import OpenAICompatibleClient

        client = OpenAICompatibleClient()
        prompt = client._build_user_prompt(
            prompt_snapshot="- 类型: 缺陷 | 关联标识: editor-copy-button | 反馈内容: copy button is invisible",
            feedback_items=[object(), object()],
        )

        self.assertIn("生成一条中文 GitHub Issue 草稿", prompt)
        self.assertIn("[缺陷]", prompt)
        self.assertIn("摘要、关联标识、用户反馈数量、背景、复现线索、期望表现、实际表现、影响范围、待补充信息、原始反馈", prompt)
        self.assertIn("用户反馈数量：2", prompt)

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

    def test_submit_draft_rejects_sensitive_credential_like_content(self) -> None:
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
        submission_service.draft_repository.update_draft(
            draft.id,
            self.DraftUpdatePayload(
                title="[缺陷] editor-copy-button",
                body_markdown="## 摘要\n包含凭据片段 ghp_1234567890abcdefghijklmnopqrstuvwxyz",
            ),
        )

        with self.assertRaises(self.RepositoryError) as raised:
            submission_service.submit_draft(draft.id)

        self.assertIn("sensitive credential-like content", str(raised.exception))

    def test_submit_draft_allows_bearer_placeholder_documentation_text(self) -> None:
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
        safe_body = "## 摘要\n文档示例里提到 Authorization: Bearer <access-token>，这里是占位符说明。"
        submission_service.draft_repository.update_draft(
            draft.id,
            self.DraftUpdatePayload(
                title="[缺陷] editor-copy-button",
                body_markdown=safe_body,
            ),
        )

        class RecordingGitHubClient:
            def __init__(self) -> None:
                self.calls: list[tuple[str, str]] = []

            def create_issue(self, *, title: str, body: str) -> dict[str, object]:
                self.calls.append((title, body))
                return {
                    "issue_number": 501,
                    "issue_url": "https://github.com/org/repo/issues/501",
                    "response_status": 201,
                    "github_state": "open",
                }

        github_client = RecordingGitHubClient()
        submission_service.github_client = github_client

        submission = submission_service.submit_draft(draft.id)

        self.assertEqual(submission.github_issue_number, 501)
        self.assertEqual(github_client.calls[0][1], safe_body)

    def test_submit_draft_allows_short_akia_like_example_text(self) -> None:
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
        safe_body = "## 摘要\n日志里出现了 AKIA1234 这样的示例片段，但它不是完整凭据。"
        submission_service.draft_repository.update_draft(
            draft.id,
            self.DraftUpdatePayload(
                title="[缺陷] editor-copy-button",
                body_markdown=safe_body,
            ),
        )

        class RecordingGitHubClient:
            def __init__(self) -> None:
                self.called = False

            def create_issue(self, *, title: str, body: str) -> dict[str, object]:
                self.called = True
                return {
                    "issue_number": 502,
                    "issue_url": "https://github.com/org/repo/issues/502",
                    "response_status": 201,
                    "github_state": "open",
                }

        github_client = RecordingGitHubClient()
        submission_service.github_client = github_client

        submission = submission_service.submit_draft(draft.id)

        self.assertEqual(submission.github_issue_number, 502)
        self.assertTrue(github_client.called)

    def test_submit_draft_rejects_overlong_title(self) -> None:
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
        original_get_draft = submission_service.draft_repository.get_draft

        def overlong_title_get_draft(draft_id: str):
            stored = original_get_draft(draft_id)
            stored.title = "[缺陷] " + ("x" * 200)
            return stored

        submission_service.draft_repository.get_draft = overlong_title_get_draft

        with self.assertRaises(self.RepositoryError) as raised:
            submission_service.submit_draft(draft.id)

        self.assertIn("safe submission limit", str(raised.exception))

    def test_submit_draft_allows_boundary_length_title_and_body(self) -> None:
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

        exact_title = "[缺陷] " + ("x" * (submission_service.MAX_GITHUB_TITLE_LENGTH - len("[缺陷] ")))
        exact_body = "x" * submission_service.MAX_GITHUB_BODY_LENGTH
        submission_service.draft_repository.update_draft(
            draft.id,
            self.DraftUpdatePayload(
                title=exact_title,
                body_markdown=exact_body,
            ),
        )

        class RecordingGitHubClient:
            def __init__(self) -> None:
                self.payload: tuple[str, str] | None = None

            def create_issue(self, *, title: str, body: str) -> dict[str, object]:
                self.payload = (title, body)
                return {
                    "issue_number": 503,
                    "issue_url": "https://github.com/org/repo/issues/503",
                    "response_status": 201,
                    "github_state": "open",
                }

        github_client = RecordingGitHubClient()
        submission_service.github_client = github_client

        submission = submission_service.submit_draft(draft.id)

        self.assertEqual(submission.github_issue_number, 503)
        self.assertEqual(github_client.payload, (exact_title, exact_body))

    def test_submit_draft_rejects_overlong_body(self) -> None:
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
        original_get_draft = submission_service.draft_repository.get_draft

        def overlong_get_draft(draft_id: str):
            stored = original_get_draft(draft_id)
            stored.body_markdown = "x" * 12001
            return stored

        submission_service.draft_repository.get_draft = overlong_get_draft

        with self.assertRaises(self.RepositoryError) as raised:
            submission_service.submit_draft(draft.id)

        self.assertIn("safe submission limit", str(raised.exception))

    def test_github_client_hides_upstream_error_body(self) -> None:
        os.environ["GITHUB_TOKEN"] = "test-token"
        os.environ["GITHUB_REPO_OWNER"] = "org"
        os.environ["GITHUB_REPO_NAME"] = "repo"

        from app.repositories import GitHubIssueClient
        from urllib.error import HTTPError
        from unittest.mock import patch

        client = GitHubIssueClient()

        http_error = HTTPError(
            url="https://api.github.com/repos/org/repo/issues",
            code=422,
            msg="unprocessable",
            hdrs=None,
            fp=None,
        )

        with patch("app.repositories.request.urlopen", side_effect=http_error):
            with self.assertRaises(self.GitHubSubmissionError) as raised:
                client.create_issue(title="[缺陷] test", body="body")

        self.assertEqual(str(raised.exception), "GitHub API request failed with status 422")


if __name__ == "__main__":
    unittest.main()
