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
    os.environ["DATABASE_URL"] = f"sqlite:///{temp_dir.name}/e2e-admin.db"
    os.environ["ADMIN_API_TOKEN"] = "secret-token"

    from fastapi.testclient import TestClient

    from app.database import initialize_database
    from app.main import app

    initialize_database()
    client = TestClient(app)

    public_headers = {"Origin": "http://testserver", "Host": "testserver"}
    admin_headers = {"X-Admin-Token": "secret-token"}

    try:
        first = client.post(
            "/api/feedback",
            headers=public_headers,
            json={
                "type": "bug",
                "related_id": "admin-batch-flow",
                "raw_content": "first admin batch item",
                "expected_behavior": "expected one",
                "actual_behavior": "actual one",
            },
        )
        second = client.post(
            "/api/feedback",
            headers=public_headers,
            json={
                "type": "bug",
                "related_id": "admin-batch-flow",
                "raw_content": "second admin batch item",
                "expected_behavior": "expected two",
                "actual_behavior": "actual two",
            },
        )
        assert first.status_code == 200, first.text
        assert second.status_code == 200, second.text

        pending = client.get("/api/admin/workbench/feedback?status=pending", headers=admin_headers)
        pending_payload = pending.json()
        assert pending.status_code == 200, pending.text
        assert pending_payload["data"]["total"] == 2, pending.text

        batch = client.post(
            "/api/admin/workbench/draft-batches",
            headers=admin_headers,
            json={
                "feedback_item_ids": [first.json()["data"]["id"], second.json()["data"]["id"]],
                "confirm_mixed_related_ids": False,
            },
        )
        batch_payload = batch.json()
        assert batch.status_code == 200, batch.text
        assert batch_payload["success"] is True, batch.text
        batch_id = batch_payload["data"]["id"]

        grouped = client.get("/api/admin/workbench/feedback?status=grouped", headers=admin_headers)
        grouped_payload = grouped.json()
        assert grouped.status_code == 200, grouped.text
        assert grouped_payload["data"]["total"] == 2, grouped.text
        assert all(item["batch_id"] == batch_id for item in grouped_payload["data"]["items"]), grouped.text

        audit = client.get(
            "/api/admin/workbench/audit-events?event_type=admin_action_succeeded&keyword=create_draft_batch&page_size=8",
            headers=admin_headers,
        )
        audit_payload = audit.json()
        assert audit.status_code == 200, audit.text
        assert audit_payload["data"]["total"] == 1, audit.text
        assert audit_payload["data"]["items"][0]["action"] == "create_draft_batch", audit.text

        print("ADMIN_BATCH_FLOW_E2E_OK")
    finally:
        client.close()
        temp_dir.cleanup()
        for key in ["APP_ENV", "DATABASE_URL", "ADMIN_API_TOKEN"]:
            os.environ.pop(key, None)


if __name__ == "__main__":
    main()
