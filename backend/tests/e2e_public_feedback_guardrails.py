import os
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    temp_dir = tempfile.TemporaryDirectory()
    os.environ["APP_ENV"] = "test"
    os.environ["DATABASE_URL"] = f"sqlite:///{temp_dir.name}/e2e.db"
    os.environ["GITHUB_TOKEN"] = "test-token"
    os.environ["GITHUB_REPO_OWNER"] = "org"
    os.environ["GITHUB_REPO_NAME"] = "repo"
    os.environ["PUBLIC_FEEDBACK_DAILY_IP_LIMIT"] = "5"
    os.environ["PUBLIC_FEEDBACK_DUPLICATE_WINDOW_MINUTES"] = "10"
    os.environ["TRUST_PROXY_HEADERS"] = "true"

    from fastapi.testclient import TestClient

    from app.database import initialize_database
    from app.main import app
    from app.repositories import DraftBatchService, DraftIntegrationService, DraftSubmissionService

    initialize_database()
    client = TestClient(app)

    try:
        blocked_origin_response = client.post(
            "/api/feedback",
            headers={"Origin": "https://evil.example"},
            json={
                "type": "bug",
                "related_id": "origin-guard-check",
                "raw_content": "cross-site request should fail",
            },
        )
        assert blocked_origin_response.status_code == 403, blocked_origin_response.text

        same_origin_headers = {
            "Origin": "http://testserver",
            "Host": "testserver",
            "X-Forwarded-For": "203.0.113.10",
        }
        for index in range(5):
            accepted = client.post(
                "/api/feedback",
                headers=same_origin_headers,
                json={
                    "type": "bug",
                    "related_id": f"daily-limit-check-{index}",
                    "raw_content": "same ip request",
                },
            )
            assert accepted.status_code == 200, accepted.text
            assert accepted.json()["success"] is True, accepted.text

        limited = client.post(
            "/api/feedback",
            headers=same_origin_headers,
            json={
                "type": "bug",
                "related_id": "daily-limit-check-blocked",
                "raw_content": "same ip request",
            },
        )
        limited_payload = limited.json()
        assert limited.status_code == 200, limited.text
        assert limited_payload["error_code"] == "FEEDBACK_DAILY_IP_LIMIT_REACHED", limited.text

        duplicate_headers = {
            "Origin": "http://testserver",
            "Host": "testserver",
            "X-Forwarded-For": "203.0.113.11",
        }
        duplicate_payload = {
            "type": "bug",
            "related_id": "duplicate-window-check",
            "raw_content": "duplicate body",
            "expected_behavior": "expected state",
            "actual_behavior": "actual state",
        }
        first_duplicate = client.post("/api/feedback", headers=duplicate_headers, json=duplicate_payload)
        second_duplicate = client.post("/api/feedback", headers=duplicate_headers, json=duplicate_payload)
        assert first_duplicate.status_code == 200, first_duplicate.text
        assert first_duplicate.json()["success"] is True, first_duplicate.text
        assert second_duplicate.status_code == 200, second_duplicate.text
        assert second_duplicate.json()["error_code"] == "FEEDBACK_DUPLICATE_CONTENT", second_duplicate.text

        history_headers = {
            "Origin": "http://testserver",
            "Host": "testserver",
            "X-Forwarded-For": "203.0.113.12",
        }
        history_feedback = client.post(
            "/api/feedback",
            headers=history_headers,
            json={
                "type": "bug",
                "related_id": "public-history-check",
                "raw_content": "history should include this issue",
            },
        )
        history_feedback_payload = history_feedback.json()
        assert history_feedback.status_code == 200, history_feedback.text
        assert history_feedback_payload["success"] is True, history_feedback.text

        batch_service = DraftBatchService()
        integration_service = DraftIntegrationService()
        submission_service = DraftSubmissionService()

        class FakeGitHubClient:
            def create_issue(self, *, title: str, body: str) -> dict[str, object]:
                return {
                    "issue_number": 901,
                    "issue_url": "https://github.com/org/repo/issues/901",
                    "response_status": 201,
                    "github_state": "open",
                }

        submission_service.github_client = FakeGitHubClient()
        batch = batch_service.create_batch([history_feedback_payload["data"]["id"]], confirm_mixed_related_ids=False)
        draft = integration_service.integrate_batch(batch.id)
        submission = submission_service.submit_draft(draft.id)
        assert submission.github_issue_number == 901

        submitted_issues = client.get("/api/issues/submitted")
        submitted_payload = submitted_issues.json()
        assert submitted_issues.status_code == 200, submitted_issues.text
        assert submitted_payload["success"] is True, submitted_issues.text
        assert submitted_payload["data"]["total"] == 1, submitted_issues.text
        assert submitted_payload["data"]["items"][0]["related_id"] == "public-history-check", submitted_issues.text

        print("PUBLIC_GUARDRAILS_E2E_OK")
    finally:
        client.close()
        temp_dir.cleanup()
        for key in [
            "APP_ENV",
            "DATABASE_URL",
            "GITHUB_TOKEN",
            "GITHUB_REPO_OWNER",
            "GITHUB_REPO_NAME",
            "PUBLIC_FEEDBACK_DAILY_IP_LIMIT",
            "PUBLIC_FEEDBACK_DUPLICATE_WINDOW_MINUTES",
            "TRUST_PROXY_HEADERS",
        ]:
            os.environ.pop(key, None)


if __name__ == "__main__":
    main()
