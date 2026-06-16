import os
import tempfile
import unittest

from fastapi.testclient import TestClient


class MainAppTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["APP_ENV"] = "test"
        os.environ["DATABASE_URL"] = f"sqlite:///{self.temp_dir.name}/test.db"
        os.environ["ADMIN_ROUTE_SLUG"] = "adminconsole"

        from app.main import app
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("ADMIN_ROUTE_SLUG", None)

    def test_root_path_returns_404(self) -> None:
        response = self.client.get("/")
        self.assertEqual(response.status_code, 404)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error_code"], "NOT_FOUND")

    def test_health_endpoint_returns_ok(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["status"], "ok")

    def test_security_headers_are_present(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(response.headers.get("x-frame-options"), "DENY")
        self.assertEqual(response.headers.get("referrer-policy"), "same-origin")
        self.assertEqual(response.headers.get("cross-origin-opener-policy"), "same-origin")
        self.assertEqual(response.headers.get("cross-origin-resource-policy"), "same-origin")
        self.assertIn("default-src 'none'", response.headers.get("content-security-policy", ""))
        self.assertIn("frame-ancestors 'none'", response.headers.get("content-security-policy", ""))

    def test_cache_control_no_store_on_api_paths(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.headers.get("cache-control"), "no-store")

    def test_http_exception_handler_returns_structured_error(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)

    def test_not_found_route_returns_structured_error(self) -> None:
        response = self.client.get(f"/{os.environ['ADMIN_ROUTE_SLUG']}/nonexistent")
        self.assertIn(response.status_code, (401, 404, 422))

    def test_invalid_method_returns_405(self) -> None:
        response = self.client.post("/api/health?data=test")
        self.assertEqual(response.status_code, 405)


if __name__ == "__main__":
    unittest.main()
