import unittest

from app.routers.health import health_check


class HealthCheckTestCase(unittest.TestCase):
    def test_health_check_returns_success(self) -> None:
        payload = health_check()

        self.assertTrue(payload["success"])
        self.assertEqual(payload["data"]["status"], "ok")


if __name__ == "__main__":
    unittest.main()
