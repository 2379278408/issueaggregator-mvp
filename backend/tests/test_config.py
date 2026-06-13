import os
import unittest

from app.config import _default_database_url


class ConfigTestCase(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("APP_ENV", None)

    def test_default_database_url_uses_dev_file_for_development(self) -> None:
        os.environ["APP_ENV"] = "development"

        self.assertTrue(_default_database_url().endswith("/backend/data/issue_aggregator.dev.db"))

    def test_default_database_url_uses_env_specific_file_for_demo(self) -> None:
        os.environ["APP_ENV"] = "demo"

        self.assertTrue(_default_database_url().endswith("/backend/data/issue_aggregator.demo.db"))

    def test_default_database_url_uses_production_file_for_production(self) -> None:
        os.environ["APP_ENV"] = "production"

        self.assertTrue(_default_database_url().endswith("/backend/data/issue_aggregator.db"))


if __name__ == "__main__":
    unittest.main()
