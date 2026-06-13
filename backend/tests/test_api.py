import os
import tempfile
import unittest
from dataclasses import replace
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

os.environ["APP_ENV"] = "test"


class ApiTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["APP_ENV"] = "test"
        os.environ["DATABASE_URL"] = f"sqlite:///{self.temp_dir.name}/test.db"

        from app.database import initialize_database
        from app.models import DraftBatchCreatePayload, DraftUpdatePayload, FeedbackCreatePayload
        from app.routers.feedback import (
            _client_ip,
            create_draft_batch,
            create_feedback,
            get_draft,
            integrate_draft_batch,
            list_audit_events,
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
        self.client_ip = _client_ip
        self.create_draft_batch = create_draft_batch
        self.create_feedback = create_feedback
        self.get_draft = get_draft
        self.integrate_draft_batch = integrate_draft_batch
        self.list_audit_events = list_audit_events
        self.list_feedback = list_feedback
        self.list_submitted_issues = list_submitted_issues
        self.require_admin_token = require_admin_token
        self.search_submitted_issues = search_submitted_issues
        self.update_draft = update_draft
        self.submission_repository = SubmissionRepository()
        self.feedback_router_module = feedback_router_module

        from app.main import app

        self.http_client = TestClient(app)

    def make_request_stub(self, *, headers: dict[str, str] | None = None, client_host: str | None = None, path: str = "/api/feedback"):
        return SimpleNamespace(
            headers=headers or {},
            client=SimpleNamespace(host=client_host) if client_host else None,
            url=SimpleNamespace(path=path),
            base_url="http://testserver/",
        )

    def tearDown(self) -> None:
        self.http_client.close()
        self.temp_dir.cleanup()
        os.environ.pop("APP_ENV", None)
        os.environ.pop("DATABASE_URL", None)

    def test_admin_router_requires_token_dependency(self) -> None:
        self.assertTrue(self.feedback_router_module.admin_router.dependencies)

    def test_admin_token_dependency_rejects_missing_or_invalid_token(self) -> None:
        original_settings = self.feedback_router_module.settings
        self.feedback_router_module.settings = replace(original_settings, admin_api_token="secret-token")
        request = self.make_request_stub(path="/api/admin/workbench/feedback")
        try:
            with self.assertRaises(HTTPException) as missing:
                self.require_admin_token(request, None)
            self.assertEqual(missing.exception.status_code, 401)

            with self.assertRaises(HTTPException) as invalid:
                self.require_admin_token(request, "wrong-token")
            self.assertEqual(invalid.exception.status_code, 401)
        finally:
            self.feedback_router_module.settings = original_settings

    def test_admin_token_dependency_accepts_configured_token(self) -> None:
        original_settings = self.feedback_router_module.settings
        self.feedback_router_module.settings = replace(original_settings, admin_api_token="secret-token")
        request = self.make_request_stub(path="/api/admin/workbench/feedback")
        try:
            self.assertIsNone(self.require_admin_token(request, "secret-token"))
        finally:
            self.feedback_router_module.settings = original_settings

    def test_admin_token_dependency_logs_failed_attempt(self) -> None:
        original_settings = self.feedback_router_module.settings
        self.feedback_router_module.settings = replace(original_settings, admin_api_token="secret-token")
        request = self.make_request_stub(client_host="8.8.8.8", path="/api/admin/workbench/feedback")
        try:
            with self.assertLogs("app.routers.feedback", level="WARNING") as captured:
                with self.assertRaises(HTTPException):
                    self.require_admin_token(request, "wrong-token")
        finally:
            self.feedback_router_module.settings = original_settings

        self.assertIn("admin_auth_failed", captured.output[0])
        self.assertIn("client_ip=8.8.8.8", captured.output[0])
        self.assertIn("event_id=", captured.output[0])
        self.assertIn("recent_count=1", captured.output[0])

    def test_admin_action_logs_successful_batch_creation(self) -> None:
        request = self.make_request_stub(client_host="8.8.8.8", path="/api/admin/workbench/draft-batches")
        first = self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item"),
            request=self.make_request_stub(),
        )

        with self.assertLogs("app.routers.feedback", level="INFO") as captured:
            response = self.create_draft_batch(
                self.DraftBatchCreatePayload(
                    feedback_item_ids=[first["data"]["id"]],
                    confirm_mixed_related_ids=False,
                ),
                request=request,
            )

        self.assertTrue(response["success"])
        self.assertIn("admin_action_succeeded", captured.output[0])
        self.assertIn("action=create_draft_batch", captured.output[0])
        self.assertIn("event_id=", captured.output[0])
        self.assertIn("recent_count=1", captured.output[0])

    def test_list_audit_events_returns_recent_records(self) -> None:
        request = self.make_request_stub(client_host="8.8.8.8", path="/api/admin/workbench/draft-batches")
        feedback = self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item"),
            request=self.make_request_stub(),
        )
        self.create_draft_batch(
            self.DraftBatchCreatePayload(
                feedback_item_ids=[feedback["data"]["id"]],
                confirm_mixed_related_ids=False,
            ),
            request=request,
        )

        response = self.list_audit_events(page=1, page_size=10)

        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["total"], 1)
        self.assertEqual(response["data"]["items"][0]["event_type"], "admin_action_succeeded")

    def test_list_audit_events_filters_by_keyword(self) -> None:
        request = self.make_request_stub(client_host="8.8.8.8", path="/api/admin/workbench/draft-batches")
        feedback = self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item"),
            request=self.make_request_stub(),
        )
        self.create_draft_batch(
            self.DraftBatchCreatePayload(
                feedback_item_ids=[feedback["data"]["id"]],
                confirm_mixed_related_ids=False,
            ),
            request=request,
        )

        response = self.list_audit_events(keyword="draft-batches", page=1, page_size=10)

        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["total"], 1)
        self.assertEqual(response["data"]["items"][0]["path"], "/api/admin/workbench/draft-batches")

    def test_list_audit_events_normalizes_whitespace_filters(self) -> None:
        request = self.make_request_stub(client_host="8.8.8.8", path="/api/admin/workbench/draft-batches")
        feedback = self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item"),
            request=self.make_request_stub(),
        )
        self.create_draft_batch(
            self.DraftBatchCreatePayload(
                feedback_item_ids=[feedback["data"]["id"]],
                confirm_mixed_related_ids=False,
            ),
            request=request,
        )

        response = self.list_audit_events(
            event_type=" admin_action_succeeded ",
            keyword=" draft-batches ",
            time_range=" all ",
            page=1,
            page_size=10,
        )

        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["total"], 1)
        self.assertEqual(response["data"]["items"][0]["event_type"], "admin_action_succeeded")

    def test_list_audit_events_returns_empty_for_non_matching_combined_filters(self) -> None:
        request = self.make_request_stub(client_host="8.8.8.8", path="/api/admin/workbench/draft-batches")
        feedback = self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item"),
            request=self.make_request_stub(),
        )
        self.create_draft_batch(
            self.DraftBatchCreatePayload(
                feedback_item_ids=[feedback["data"]["id"]],
                confirm_mixed_related_ids=False,
            ),
            request=request,
        )

        response = self.list_audit_events(
            event_type="admin_auth_failed",
            keyword="batch_missing",
            time_range="10m",
            page=1,
            page_size=10,
        )

        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["total"], 0)
        self.assertEqual(response["data"]["items"], [])

    def test_list_audit_events_rejects_invalid_time_range(self) -> None:
        with self.assertRaises(HTTPException) as captured:
            self.list_audit_events(time_range="7d", page=1, page_size=10)

        self.assertEqual(captured.exception.status_code, 400)

    def test_list_audit_events_rejects_overlong_keyword(self) -> None:
        with self.assertRaises(HTTPException) as captured:
            self.list_audit_events(keyword="x" * 121, page=1, page_size=10)

        self.assertEqual(captured.exception.status_code, 400)

    def test_list_audit_events_rejects_invalid_event_type(self) -> None:
        with self.assertRaises(HTTPException) as captured:
            self.list_audit_events(event_type="unexpected", page=1, page_size=10)

        self.assertEqual(captured.exception.status_code, 400)

    def test_list_audit_events_rejects_invalid_pagination(self) -> None:
        with self.assertRaises(HTTPException) as captured:
            self.list_audit_events(page=0, page_size=101)

        self.assertEqual(captured.exception.status_code, 400)

    def test_create_feedback_success(self) -> None:
        payload = self.FeedbackCreatePayload(
            type="bug",
            related_id="editor-copy-button",
            raw_content="复制按钮在暗色模式下不可见",
            expected_behavior="按钮可见",
            actual_behavior="按钮颜色过浅",
        )
        response = self.create_feedback(payload, request=self.make_request_stub())

        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["status"], "pending")
        self.assertTrue(response["data"]["id"].startswith("fb_"))

    def test_create_feedback_enforces_daily_ip_limit(self) -> None:
        for index in range(5):
            response = self.create_feedback(
                self.FeedbackCreatePayload(
                    type="bug",
                    related_id=f"editor-copy-button-{index}",
                    raw_content="复制按钮在暗色模式下不可见",
                ),
                request=self.make_request_stub(),
            )
            self.assertTrue(response["success"])

        blocked = self.create_feedback(
            self.FeedbackCreatePayload(
                type="bug",
                related_id="editor-copy-button-limit",
                raw_content="复制按钮在暗色模式下不可见",
            ),
            request=self.make_request_stub(),
        )

        self.assertFalse(blocked["success"])
        self.assertEqual(blocked["error_code"], "FEEDBACK_DAILY_IP_LIMIT_REACHED")

    def test_create_feedback_rejects_recent_duplicate_content(self) -> None:
        payload = self.FeedbackCreatePayload(
            type="bug",
            related_id="editor-copy-button",
            raw_content="复制按钮在暗色模式下不可见",
            expected_behavior="按钮可见",
            actual_behavior="按钮颜色过浅",
        )

        first = self.create_feedback(payload, request=self.make_request_stub())
        duplicate = self.create_feedback(payload, request=self.make_request_stub())

        self.assertTrue(first["success"])
        self.assertFalse(duplicate["success"])
        self.assertEqual(duplicate["error_code"], "FEEDBACK_DUPLICATE_CONTENT")

    def test_client_ip_ignores_forwarded_for_by_default(self) -> None:
        original_settings = self.feedback_router_module.settings
        self.feedback_router_module.settings = replace(original_settings, trust_proxy_headers=False)
        request = SimpleNamespace(
            headers={"x-forwarded-for": "9.9.9.9, 149.112.112.112"},
            client=SimpleNamespace(host="8.8.8.8"),
        )
        try:
            self.assertEqual(self.client_ip(request), "8.8.8.8")
        finally:
            self.feedback_router_module.settings = original_settings

    def test_client_ip_uses_forwarded_for_when_proxy_headers_are_trusted(self) -> None:
        original_settings = self.feedback_router_module.settings
        self.feedback_router_module.settings = replace(original_settings, trust_proxy_headers=True)
        request = SimpleNamespace(
            headers={"x-forwarded-for": "9.9.9.9, 149.112.112.112"},
            client=SimpleNamespace(host="8.8.8.8"),
        )
        try:
            self.assertEqual(self.client_ip(request), "9.9.9.9")
        finally:
            self.feedback_router_module.settings = original_settings

    def test_client_ip_falls_back_when_forwarded_for_is_invalid(self) -> None:
        original_settings = self.feedback_router_module.settings
        self.feedback_router_module.settings = replace(original_settings, trust_proxy_headers=True)
        request = SimpleNamespace(
            headers={"x-forwarded-for": "not-an-ip"},
            client=SimpleNamespace(host="8.8.8.8"),
        )
        try:
            self.assertEqual(self.client_ip(request), "8.8.8.8")
        finally:
            self.feedback_router_module.settings = original_settings

    def test_client_ip_skips_private_proxy_address_when_headers_are_untrusted(self) -> None:
        original_settings = self.feedback_router_module.settings
        self.feedback_router_module.settings = replace(original_settings, trust_proxy_headers=False)
        request = SimpleNamespace(
            headers={"x-forwarded-for": "9.9.9.9, 149.112.112.112"},
            client=SimpleNamespace(host="10.0.0.12"),
        )
        try:
            self.assertEqual(self.client_ip(request), "9.9.9.9")
        finally:
            self.feedback_router_module.settings = original_settings

    def test_client_ip_returns_none_when_request_has_no_usable_ip(self) -> None:
        request = SimpleNamespace(headers={}, client=None)

        self.assertIsNone(self.client_ip(request))

    def test_create_feedback_skips_daily_limit_when_client_ip_is_unavailable(self) -> None:
        for index in range(6):
            response = self.create_feedback(
                self.FeedbackCreatePayload(
                    type="bug",
                    related_id=f"missing-ip-{index}",
                    raw_content="复制按钮在暗色模式下不可见",
                ),
                request=self.make_request_stub(),
                client_ip=None,
            )
            self.assertTrue(response["success"])

    def test_public_feedback_rejects_cross_origin_browser_requests_by_default(self) -> None:
        response = self.http_client.post(
            "/api/feedback",
            headers={"Origin": "https://evil.example"},
            json={
                "type": "bug",
                "related_id": "editor-copy-button",
                "raw_content": "cross origin attempt",
            },
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["message"], "Origin is not allowed")

    def test_public_feedback_accepts_same_origin_browser_requests(self) -> None:
        response = self.http_client.post(
            "/api/feedback",
            headers={"Origin": "http://testserver"},
            json={
                "type": "bug",
                "related_id": "editor-copy-button",
                "raw_content": "same origin request",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_public_feedback_accepts_origin_when_host_header_matches_proxy_domain(self) -> None:
        response = self.http_client.post(
            "/api/feedback",
            headers={
                "Origin": "https://public.example.com",
                "Host": "public.example.com",
            },
            json={
                "type": "bug",
                "related_id": "editor-copy-button",
                "raw_content": "proxied same-origin request",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

    def test_public_feedback_accepts_configured_origin_allowlist(self) -> None:
        original_settings = self.feedback_router_module.settings
        self.feedback_router_module.settings = replace(
            original_settings,
            public_feedback_allowed_origins=("https://preview.example.com",),
        )
        try:
            response = self.http_client.post(
                "/api/feedback",
                headers={"Origin": "https://preview.example.com"},
                json={
                    "type": "bug",
                    "related_id": "editor-copy-button",
                    "raw_content": "allowlisted origin request",
                },
            )
        finally:
            self.feedback_router_module.settings = original_settings

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])

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
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item"),
            request=self.make_request_stub(),
        )
        self.create_feedback(
            self.FeedbackCreatePayload(type="feature", related_id="login-oauth-flow", raw_content="second item"),
            request=self.make_request_stub(),
        )

        response = self.list_feedback(status="pending")

        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["total"], 2)
        self.assertEqual(response["data"]["items"][0]["status"], "pending")

    def test_create_draft_batch_success(self) -> None:
        first = self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item"),
            request=self.make_request_stub(),
        )
        second = self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="second item"),
            request=self.make_request_stub(),
        )

        response = self.create_draft_batch(
            self.DraftBatchCreatePayload(
                feedback_item_ids=[first["data"]["id"], second["data"]["id"]],
                confirm_mixed_related_ids=False,
            ),
            request=self.make_request_stub(path="/api/admin/workbench/draft-batches"),
        )

        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["status"], "created")
        self.assertEqual(response["data"]["primary_related_id"], "editor-copy-button")
        self.assertEqual(response["data"]["related_id_count"], 1)

    def test_create_draft_batch_requires_mixed_related_id_confirmation(self) -> None:
        first = self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item"),
            request=self.make_request_stub(),
        )
        second = self.create_feedback(
            self.FeedbackCreatePayload(type="feature", related_id="login-oauth-flow", raw_content="second item"),
            request=self.make_request_stub(),
        )

        response = self.create_draft_batch(
            self.DraftBatchCreatePayload(
                feedback_item_ids=[first["data"]["id"], second["data"]["id"]],
                confirm_mixed_related_ids=False,
            ),
            request=self.make_request_stub(path="/api/admin/workbench/draft-batches"),
        )

        self.assertFalse(response["success"])
        self.assertEqual(response["error_code"], "MIXED_RELATED_ID_CONFIRM_REQUIRED")

    def test_create_draft_batch_marks_feedback_as_grouped(self) -> None:
        first = self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item"),
            request=self.make_request_stub(),
        )

        self.create_draft_batch(
            self.DraftBatchCreatePayload(
                feedback_item_ids=[first["data"]["id"]],
                confirm_mixed_related_ids=False,
            ),
            request=self.make_request_stub(path="/api/admin/workbench/draft-batches"),
        )

        grouped_response = self.list_feedback(status="grouped")
        self.assertEqual(grouped_response["data"]["total"], 1)
        self.assertEqual(grouped_response["data"]["items"][0]["id"], first["data"]["id"])
        self.assertTrue(grouped_response["data"]["items"][0]["batch_id"].startswith("batch_"))

    def test_integrate_batch_returns_draft(self) -> None:
        first = self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item"),
            request=self.make_request_stub(),
        )
        batch = self.create_draft_batch(
            self.DraftBatchCreatePayload(
                feedback_item_ids=[first["data"]["id"]],
                confirm_mixed_related_ids=False,
            ),
            request=self.make_request_stub(path="/api/admin/workbench/draft-batches"),
        )

        response = self.integrate_draft_batch(
            batch["data"]["id"],
            request=self.make_request_stub(path=f"/api/admin/workbench/draft-batches/{batch['data']['id']}/integrate"),
        )

        self.assertTrue(response["success"])
        self.assertEqual(response["data"]["status"], "draft_ready")

    def test_get_and_update_draft(self) -> None:
        first = self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item"),
            request=self.make_request_stub(),
        )
        batch = self.create_draft_batch(
            self.DraftBatchCreatePayload(
                feedback_item_ids=[first["data"]["id"]],
                confirm_mixed_related_ids=False,
            ),
            request=self.make_request_stub(path="/api/admin/workbench/draft-batches"),
        )
        integrate_response = self.integrate_draft_batch(
            batch["data"]["id"],
            request=self.make_request_stub(path=f"/api/admin/workbench/draft-batches/{batch['data']['id']}/integrate"),
        )
        draft_id = integrate_response["data"]["draft_id"]

        draft_response = self.get_draft(draft_id)
        update_response = self.update_draft(
            draft_id,
            self.DraftUpdatePayload(title="Updated title", body_markdown="Updated body"),
            request=self.make_request_stub(path=f"/api/admin/workbench/drafts/{draft_id}"),
        )

        self.assertTrue(draft_response["success"])
        self.assertEqual(draft_response["data"]["id"], draft_id)
        self.assertTrue(update_response["success"])
        self.assertEqual(update_response["data"]["id"], draft_id)

    def test_submit_draft_returns_submission_payload(self) -> None:
        first = self.create_feedback(
            self.FeedbackCreatePayload(type="bug", related_id="editor-copy-button", raw_content="first item"),
            request=self.make_request_stub(),
        )
        batch = self.create_draft_batch(
            self.DraftBatchCreatePayload(
                feedback_item_ids=[first["data"]["id"]],
                confirm_mixed_related_ids=False,
            ),
            request=self.make_request_stub(path="/api/admin/workbench/draft-batches"),
        )
        integrate_response = self.integrate_draft_batch(
            batch["data"]["id"],
            request=self.make_request_stub(path=f"/api/admin/workbench/draft-batches/{batch['data']['id']}/integrate"),
        )
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
            response = self.feedback_router_module.submit_draft(
                draft_id,
                request=self.make_request_stub(path=f"/api/admin/workbench/drafts/{draft_id}/submit"),
            )
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
            response = self.feedback_router_module.submit_draft(
                "draft_1234567890ab",
                request=self.make_request_stub(path="/api/admin/workbench/drafts/draft_1234567890ab/submit"),
            )
        finally:
            self.feedback_router_module.draft_submission_service = original_service

        self.assertFalse(response["success"])
        self.assertEqual(response["error_code"], "TOKEN_MISSING")

    def test_submit_draft_returns_content_rejected_for_sensitive_body(self) -> None:
        class SensitiveDraftSubmissionService:
            def submit_draft(self, _: str):
                from app.repositories import RepositoryError

                raise RepositoryError("Draft content contains sensitive credential-like content")

        original_service = self.feedback_router_module.draft_submission_service
        self.feedback_router_module.draft_submission_service = SensitiveDraftSubmissionService()
        try:
            response = self.feedback_router_module.submit_draft(
                "draft_1234567890ab",
                request=self.make_request_stub(path="/api/admin/workbench/drafts/draft_1234567890ab/submit"),
            )
        finally:
            self.feedback_router_module.draft_submission_service = original_service

        self.assertFalse(response["success"])
        self.assertEqual(response["error_code"], "DRAFT_CONTENT_REJECTED")

    def test_api_responses_include_security_headers(self) -> None:
        response = self.http_client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        self.assertEqual(response.headers["referrer-policy"], "same-origin")
        self.assertEqual(response.headers["cross-origin-opener-policy"], "same-origin")
        self.assertEqual(response.headers["cross-origin-resource-policy"], "same-origin")
        self.assertEqual(response.headers["content-security-policy"], "default-src 'none'; frame-ancestors 'none'; base-uri 'none'")
        self.assertEqual(response.headers["cache-control"], "no-store")

    def test_docs_endpoint_is_disabled_by_default(self) -> None:
        response = self.http_client.get("/docs")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
