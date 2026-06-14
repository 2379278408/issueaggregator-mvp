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
    os.environ["DATABASE_URL"] = f"sqlite:///{temp_dir.name}/e2e-submit.db"
    os.environ["ADMIN_API_TOKEN"] = "secret-token"
    os.environ["GITHUB_TOKEN"] = "test-token"
    os.environ["GITHUB_REPO_OWNER"] = "org"
    os.environ["GITHUB_REPO_NAME"] = "repo"

    from fastapi.testclient import TestClient

    from app.database import initialize_database
    from app.main import app
    from app.repositories import DraftSubmissionService
    from app.routers import feedback as feedback_router_module

    initialize_database()
    client = TestClient(app)

    public_headers = {"Origin": "http://testserver", "Host": "testserver"}
    admin_headers = {"X-Admin-Token": "secret-token"}

    original_submission_service = feedback_router_module.draft_submission_service
    submission_service = DraftSubmissionService()

    class FakeGitHubClient:
        def create_issue(self, *, title: str, body: str) -> dict[str, object]:
            return {
                "issue_number": 902,
                "issue_url": "https://github.com/org/repo/issues/902",
                "response_status": 201,
                "github_state": "open",
            }

    submission_service.github_client = FakeGitHubClient()
    feedback_router_module.draft_submission_service = submission_service

    try:
        feedback = client.post(
            "/api/feedback",
            headers=public_headers,
            json={
                "type": "bug",
                "related_id": "github-submit-flow",
                "raw_content": "submit flow item",
                "expected_behavior": "expected state",
                "actual_behavior": "actual state",
            },
        )
        assert feedback.status_code == 200, feedback.text
        feedback_id = feedback.json()["data"]["id"]

        batch = client.post(
            "/api/admin/workbench/draft-batches",
            headers=admin_headers,
            json={
                "feedback_item_ids": [feedback_id],
                "confirm_mixed_related_ids": False,
            },
        )
        assert batch.status_code == 200, batch.text
        batch_id = batch.json()["data"]["id"]

        integrate = client.post(
            f"/api/admin/workbench/draft-batches/{batch_id}/integrate",
            headers=admin_headers,
            json={},
        )
        assert integrate.status_code == 200, integrate.text
        draft_id = integrate.json()["data"]["draft_id"]

        update = client.put(
            f"/api/admin/workbench/drafts/{draft_id}",
            headers=admin_headers,
            json={
                "title": "[缺陷] github-submit-flow 提交验证",
                "body_markdown": "## 摘要\n提交前验证\n## 影响\n需要记录审计事件",
            },
        )
        assert update.status_code == 200, update.text

        submit = client.post(
            f"/api/admin/workbench/drafts/{draft_id}/submit",
            headers=admin_headers,
            json={},
        )
        submit_payload = submit.json()
        assert submit.status_code == 200, submit.text
        assert submit_payload["success"] is True, submit.text
        assert submit_payload["data"]["issue_number"] == 902, submit.text

        submitted = client.get("/api/issues/submitted/search?related_id=github-submit-flow")
        submitted_payload = submitted.json()
        assert submitted.status_code == 200, submitted.text
        assert submitted_payload["data"]["total"] == 1, submitted.text
        assert submitted_payload["data"]["items"][0]["issue_number"] == 902, submitted.text

        audit = client.get(
            "/api/admin/workbench/audit-events?event_type=admin_action_succeeded&keyword=submit_draft&page_size=8",
            headers=admin_headers,
        )
        audit_payload = audit.json()
        assert audit.status_code == 200, audit.text
        assert audit_payload["data"]["total"] == 1, audit.text
        assert audit_payload["data"]["items"][0]["action"] == "submit_draft", audit.text

        print("GITHUB_SUBMIT_FLOW_E2E_OK")
    finally:
        feedback_router_module.draft_submission_service = original_submission_service
        client.close()
        temp_dir.cleanup()
        for key in [
            "APP_ENV",
            "DATABASE_URL",
            "ADMIN_API_TOKEN",
            "GITHUB_TOKEN",
            "GITHUB_REPO_OWNER",
            "GITHUB_REPO_NAME",
        ]:
            os.environ.pop(key, None)


if __name__ == "__main__":
    main()
