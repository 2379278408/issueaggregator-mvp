import os
import unittest

from app.config import (
    Settings,
    _default_database_url,
    _production_required,
    _require_env,
    _split_csv_env,
    _validate_admin_route_slug,
    _validate_admin_security_settings,
    get_settings,
)


class RequireEnvTestCase(unittest.TestCase):
    def test_returns_value_when_present(self) -> None:
        os.environ["TEST_VAR"] = "hello"
        self.assertEqual(_require_env("TEST_VAR"), "hello")

    def test_returns_value_when_present_with_whitespace(self) -> None:
        os.environ["TEST_VAR"] = "  trimmed  "
        self.assertEqual(_require_env("TEST_VAR"), "trimmed")

    def test_raises_system_exit_when_missing(self) -> None:
        with self.assertRaises(SystemExit):
            _require_env("NONEXISTENT_VAR")

    def test_raises_system_exit_when_empty(self) -> None:
        os.environ["TEST_VAR"] = ""
        with self.assertRaises(SystemExit):
            _require_env("TEST_VAR")

    def tearDown(self) -> None:
        os.environ.pop("TEST_VAR", None)


class ProductionRequiredTestCase(unittest.TestCase):
    def test_returns_value_when_present(self) -> None:
        self.assertEqual(_production_required("FIELD", "value"), "value")

    def test_raises_system_exit_when_none(self) -> None:
        with self.assertRaises(SystemExit):
            _production_required("FIELD", None)

    def test_raises_system_exit_when_empty_string(self) -> None:
        with self.assertRaises(SystemExit):
            _production_required("FIELD", "")


class ValidateAdminRouteSlugTestCase(unittest.TestCase):
    def test_accepts_eight_chars(self) -> None:
        self.assertEqual(_validate_admin_route_slug("abcdefgh"), "abcdefgh")

    def test_accepts_64_chars(self) -> None:
        slug = "a" * 64
        self.assertEqual(_validate_admin_route_slug(slug), slug)

    def test_accepts_mixed_lowercase_and_digits(self) -> None:
        self.assertEqual(_validate_admin_route_slug("abc12345"), "abc12345")

    def test_rejects_too_short(self) -> None:
        with self.assertRaises(SystemExit):
            _validate_admin_route_slug("abc1234")

    def test_rejects_too_long(self) -> None:
        with self.assertRaises(SystemExit):
            _validate_admin_route_slug("a" * 65)

    def test_rejects_empty_string(self) -> None:
        with self.assertRaises(SystemExit):
            _validate_admin_route_slug("")

    def test_rejects_whitespace_only(self) -> None:
        with self.assertRaises(SystemExit):
            _validate_admin_route_slug("        ")

    def test_rejects_uppercase_letters(self) -> None:
        with self.assertRaises(SystemExit):
            _validate_admin_route_slug("Abcdefgh")

    def test_rejects_special_characters(self) -> None:
        with self.assertRaises(SystemExit):
            _validate_admin_route_slug("abcdefg-h")

    def test_rejects_underscore(self) -> None:
        with self.assertRaises(SystemExit):
            _validate_admin_route_slug("abcd_efgh")

    def test_accepts_default_adminconsole(self) -> None:
        self.assertEqual(_validate_admin_route_slug("adminconsole"), "adminconsole")


class SplitCsvEnvTestCase(unittest.TestCase):
    def test_single_domain(self) -> None:
        os.environ["TEST_CSV"] = "example.com"
        result = _split_csv_env("TEST_CSV")
        self.assertEqual(result, ("example.com",))

    def test_multiple_domains(self) -> None:
        os.environ["TEST_CSV"] = "example.com,test.org"
        result = _split_csv_env("TEST_CSV")
        self.assertEqual(result, ("example.com", "test.org"))

    def test_trims_whitespace(self) -> None:
        os.environ["TEST_CSV"] = " example.com ,  test.org "
        result = _split_csv_env("TEST_CSV")
        self.assertEqual(result, ("example.com", "test.org"))

    def test_strips_trailing_slashes(self) -> None:
        os.environ["TEST_CSV"] = "example.com/, test.org/"
        result = _split_csv_env("TEST_CSV")
        self.assertEqual(result, ("example.com", "test.org"))

    def test_empty_string_returns_empty_tuple(self) -> None:
        os.environ["TEST_CSV"] = ""
        result = _split_csv_env("TEST_CSV")
        self.assertEqual(result, ())

    def test_missing_var_returns_empty_tuple(self) -> None:
        result = _split_csv_env("NONEXISTENT_CSV")
        self.assertEqual(result, ())

    def test_only_commas_returns_empty_tuple(self) -> None:
        os.environ["TEST_CSV"] = ", ,"
        result = _split_csv_env("TEST_CSV")
        self.assertEqual(result, ())

    def tearDown(self) -> None:
        os.environ.pop("TEST_CSV", None)


class DefaultDatabaseUrlTestCase(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop("APP_ENV", None)

    def test_development_uses_dev_db(self) -> None:
        os.environ["APP_ENV"] = "development"
        self.assertTrue(_default_database_url().endswith("/backend/data/issue_aggregator.dev.db"))

    def test_empty_string_defaults_to_dev(self) -> None:
        os.environ["APP_ENV"] = ""
        self.assertTrue(_default_database_url().endswith("/backend/data/issue_aggregator.dev.db"))

    def test_local_defaults_to_dev(self) -> None:
        os.environ["APP_ENV"] = "local"
        self.assertTrue(_default_database_url().endswith("/backend/data/issue_aggregator.dev.db"))

    def test_dev_defaults_to_dev(self) -> None:
        os.environ["APP_ENV"] = "dev"
        self.assertTrue(_default_database_url().endswith("/backend/data/issue_aggregator.dev.db"))

    def test_production_uses_base_db(self) -> None:
        os.environ["APP_ENV"] = "production"
        self.assertTrue(_default_database_url().endswith("/backend/data/issue_aggregator.db"))

    def test_prod_uses_base_db(self) -> None:
        os.environ["APP_ENV"] = "prod"
        self.assertTrue(_default_database_url().endswith("/backend/data/issue_aggregator.db"))

    def test_custom_env_uses_labeled_db(self) -> None:
        os.environ["APP_ENV"] = "staging"
        self.assertTrue(_default_database_url().endswith("/backend/data/issue_aggregator.staging.db"))

    def test_env_with_special_chars_is_sanitized(self) -> None:
        os.environ["APP_ENV"] = "test/env!"
        self.assertTrue(_default_database_url().endswith("/backend/data/issue_aggregator.test-env-.db"))


class ValidateAdminSecuritySettingsTestCase(unittest.TestCase):
    def test_production_all_present_passes(self) -> None:
        _validate_admin_security_settings("production", "admin", "hash", "secret")

    def test_production_missing_username_raises(self) -> None:
        with self.assertRaises(SystemExit):
            _validate_admin_security_settings("production", None, "hash", "secret")

    def test_production_missing_password_hash_raises(self) -> None:
        with self.assertRaises(SystemExit):
            _validate_admin_security_settings("production", "admin", None, "secret")

    def test_production_missing_session_secret_raises(self) -> None:
        with self.assertRaises(SystemExit):
            _validate_admin_security_settings("production", "admin", "hash", None)

    def test_development_missing_fields_passes(self) -> None:
        _validate_admin_security_settings("development", None, None, None)

    def test_prod_alias_also_enforces(self) -> None:
        with self.assertRaises(SystemExit):
            _validate_admin_security_settings("prod", None, "hash", "secret")


class GetSettingsDefaultsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["APP_NAME"] = "TestApp"
        os.environ["ADMIN_ROUTE_SLUG"] = "adminconsole"

    def tearDown(self) -> None:
        for key in list(os.environ.keys()):
            if key.startswith("APP_") or key.startswith("ADMIN_") or key.startswith("AI_") or key.startswith("GITHUB_") or key.startswith("RATE_") or key.startswith("RELATED_") or key.startswith("PUBLIC_") or key.startswith("TRUST_") or key in ("ENABLE_API_DOCS", "DATABASE_URL", "API_BASE_PATH", "TEST_VAR"):
                os.environ.pop(key, None)

    def test_app_name_default_is_set(self) -> None:
        settings = get_settings()
        self.assertEqual(settings.app_name, "TestApp")

    def test_api_base_path_default(self) -> None:
        settings = get_settings()
        self.assertEqual(settings.api_base_path, "/api")

    def test_admin_session_idle_minutes_default(self) -> None:
        settings = get_settings()
        self.assertEqual(settings.admin_session_idle_minutes, 120)

    def test_admin_session_max_hours_default(self) -> None:
        settings = get_settings()
        self.assertEqual(settings.admin_session_max_hours, 24)

    def test_admin_login_failure_limit_default(self) -> None:
        settings = get_settings()
        self.assertEqual(settings.admin_login_failure_limit, 5)

    def test_admin_login_failure_window_default(self) -> None:
        settings = get_settings()
        self.assertEqual(settings.admin_login_failure_window_minutes, 15)

    def test_admin_login_cooldown_default(self) -> None:
        settings = get_settings()
        self.assertEqual(settings.admin_login_cooldown_minutes, 30)

    def test_public_feedback_daily_ip_limit_default(self) -> None:
        settings = get_settings()
        self.assertEqual(settings.public_feedback_daily_ip_limit, 5)

    def test_rate_limit_per_hour_default(self) -> None:
        settings = get_settings()
        self.assertEqual(settings.rate_limit_per_hour, 20)

    def test_enable_api_docs_default_false(self) -> None:
        settings = get_settings()
        self.assertFalse(settings.enable_api_docs)

    def test_trust_proxy_headers_default_false(self) -> None:
        settings = get_settings()
        self.assertFalse(settings.trust_proxy_headers)

    def test_public_feedback_allowed_origins_default_empty(self) -> None:
        settings = get_settings()
        self.assertEqual(settings.public_feedback_allowed_origins, ())

    def test_admin_api_namespace_default(self) -> None:
        settings = get_settings()
        self.assertEqual(settings.admin_api_namespace, "workbench")


class GetSettingsWithEnvTestCase(unittest.TestCase):
    def setUp(self) -> None:
        os.environ["APP_ENV"] = "test"
        os.environ["ADMIN_ROUTE_SLUG"] = "adminconsole"

    def tearDown(self) -> None:
        for key in list(os.environ.keys()):
            if key.startswith("APP_") or key.startswith("ADMIN_") or key.startswith("AI_") or key.startswith("GITHUB_") or key.startswith("RATE_") or key.startswith("RELATED_") or key.startswith("PUBLIC_") or key.startswith("TRUST_") or key in ("ENABLE_API_DOCS", "DATABASE_URL", "API_BASE_PATH", "TEST_VAR"):
                os.environ.pop(key, None)

    def test_override_public_feedback_daily_ip_limit(self) -> None:
        os.environ["PUBLIC_FEEDBACK_DAILY_IP_LIMIT"] = "10"
        settings = get_settings()
        self.assertEqual(settings.public_feedback_daily_ip_limit, 10)

    def test_override_admin_session_idle_minutes(self) -> None:
        os.environ["ADMIN_SESSION_IDLE_MINUTES"] = "60"
        settings = get_settings()
        self.assertEqual(settings.admin_session_idle_minutes, 60)

    def test_override_enable_api_docs_true(self) -> None:
        os.environ["ENABLE_API_DOCS"] = "true"
        settings = get_settings()
        self.assertTrue(settings.enable_api_docs)

    def test_trust_proxy_headers_on(self) -> None:
        os.environ["TRUST_PROXY_HEADERS"] = "yes"
        settings = get_settings()
        self.assertTrue(settings.trust_proxy_headers)

    def test_admin_setting_defaults_are_none_in_test_env(self) -> None:
        settings = get_settings()
        self.assertIsNone(settings.admin_username)
        self.assertIsNone(settings.admin_password_hash)
        self.assertIsNone(settings.admin_session_secret)


if __name__ == "__main__":
    unittest.main()
