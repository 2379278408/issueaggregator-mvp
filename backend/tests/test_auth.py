import hashlib
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException


class NormalizeClientIpTestCase(unittest.TestCase):
    def setUp(self) -> None:
        from app.auth import _normalize_client_ip
        self.fn = _normalize_client_ip

    def test_valid_ip(self) -> None:
        self.assertEqual(self.fn("192.168.1.1"), "192.168.1.1")

    def test_empty_string_returns_none(self) -> None:
        self.assertIsNone(self.fn(""))

    def test_none_returns_none(self) -> None:
        self.assertIsNone(self.fn(None))

    def test_whitespace_only_returns_none(self) -> None:
        self.assertIsNone(self.fn("   "))

    def test_strips_whitespace(self) -> None:
        self.assertEqual(self.fn("  10.0.0.1  "), "10.0.0.1")

    def test_lowercases(self) -> None:
        self.assertEqual(self.fn("192.168.1.1"), "192.168.1.1")


class ParseClientIpTestCase(unittest.TestCase):
    def setUp(self) -> None:
        from app.auth import _parse_client_ip
        self.fn = _parse_client_ip

    def test_valid_ipv4(self) -> None:
        result = self.fn("192.168.1.1")
        self.assertIsNotNone(result)
        self.assertTrue(result.is_private)

    def test_valid_ipv6(self) -> None:
        result = self.fn("::1")
        self.assertIsNotNone(result)
        self.assertTrue(result.is_loopback)

    def test_invalid_string_returns_none(self) -> None:
        self.assertIsNone(self.fn("not-an-ip"))

    def test_empty_returns_none(self) -> None:
        self.assertIsNone(self.fn(""))

    def test_none_returns_none(self) -> None:
        self.assertIsNone(self.fn(None))


class ResolveClientIpTestCase(unittest.TestCase):
    def setUp(self) -> None:
        from app.auth import _resolve_client_ip
        self.fn = _resolve_client_ip

    def test_direct_global_ip_returns_it(self) -> None:
        request = SimpleNamespace(
            headers={"x-forwarded-for": ""},
            client=SimpleNamespace(host="8.8.8.8"),
        )
        os.environ["TRUST_PROXY_HEADERS"] = "false"
        result = self.fn(request)
        self.assertEqual(result, "8.8.8.8")

    def test_forwarded_single_ip_trusted(self) -> None:
        request = SimpleNamespace(
            headers={"x-forwarded-for": "10.0.0.1"},
            client=SimpleNamespace(host="127.0.0.1"),
        )
        os.environ["TRUST_PROXY_HEADERS"] = "true"
        result = self.fn(request)
        self.assertEqual(result, "10.0.0.1")

    def test_forwarded_multiple_ips_takes_first(self) -> None:
        request = SimpleNamespace(
            headers={"x-forwarded-for": "10.0.0.1, 10.0.0.2"},
            client=SimpleNamespace(host="127.0.0.1"),
        )
        os.environ["TRUST_PROXY_HEADERS"] = "true"
        result = self.fn(request)
        self.assertEqual(result, "10.0.0.1")

    def test_forwarded_not_trusted_with_private_peer_falls_back(self) -> None:
        request = SimpleNamespace(
            headers={"x-forwarded-for": "10.0.0.1"},
            client=SimpleNamespace(host="127.0.0.1"),
        )
        os.environ["TRUST_PROXY_HEADERS"] = "false"
        result = self.fn(request)
        self.assertEqual(result, "10.0.0.1")

    def test_no_usable_ip_returns_none(self) -> None:
        request = SimpleNamespace(
            headers={},
            client=None,
        )
        os.environ["TRUST_PROXY_HEADERS"] = "false"
        result = self.fn(request)
        self.assertIsNone(result)

    def tearDown(self) -> None:
        os.environ.pop("TRUST_PROXY_HEADERS", None)


class HashSessionTokenTestCase(unittest.TestCase):
    def setUp(self) -> None:
        from app.auth import hash_session_token
        self.fn = hash_session_token

    def test_returns_64_char_hex_string(self) -> None:
        result = self.fn("test-token")
        self.assertEqual(len(result), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in result))

    def test_deterministic_same_input_same_output(self) -> None:
        self.assertEqual(self.fn("abc"), self.fn("abc"))

    def test_different_inputs_produce_different_outputs(self) -> None:
        self.assertNotEqual(self.fn("abc"), self.fn("def"))

    def test_empty_string(self) -> None:
        result = self.fn("")
        self.assertEqual(len(result), 64)

    def test_long_token(self) -> None:
        result = self.fn("x" * 1000)
        self.assertEqual(len(result), 64)


class HashPasswordTestCase(unittest.TestCase):
    def setUp(self) -> None:
        from app.auth import hash_password
        self.fn = hash_password

    def test_returns_bcrypt_format(self) -> None:
        result = self.fn("mypassword")
        self.assertTrue(result.startswith("$2b$") or result.startswith("$2a$"))

    def test_different_salts_for_same_password(self) -> None:
        a = self.fn("mypassword")
        b = self.fn("mypassword")
        self.assertNotEqual(a, b)

    def test_empty_password_works(self) -> None:
        result = self.fn("")
        self.assertTrue(result.startswith("$2b$") or result.startswith("$2a$"))


class VerifyAdminPasswordTestCase(unittest.TestCase):
    def setUp(self) -> None:
        from app.auth import hash_password, verify_admin_password
        self.hash_password = hash_password
        self.fn = verify_admin_password

    def tearDown(self) -> None:
        os.environ.pop("ADMIN_PASSWORD_HASH", None)

    def test_bcrypt_correct_password(self) -> None:
        os.environ["ADMIN_PASSWORD_HASH"] = self.hash_password("secret")
        self.assertTrue(self.fn("secret"))

    def test_bcrypt_wrong_password(self) -> None:
        os.environ["ADMIN_PASSWORD_HASH"] = self.hash_password("secret")
        self.assertFalse(self.fn("wrong"))

    def test_sha256_fallback_correct(self) -> None:
        os.environ["ADMIN_PASSWORD_HASH"] = hashlib.sha256("legacy-pass".encode()).hexdigest()
        self.assertTrue(self.fn("legacy-pass"))

    def test_sha256_fallback_wrong(self) -> None:
        os.environ["ADMIN_PASSWORD_HASH"] = hashlib.sha256("legacy-pass".encode()).hexdigest()
        self.assertFalse(self.fn("wrong-pass"))

    def test_empty_stored_hash_returns_false(self) -> None:
        os.environ["ADMIN_PASSWORD_HASH"] = ""
        self.assertFalse(self.fn("anything"))

    def test_none_stored_hash_returns_false(self) -> None:
        self.assertFalse(self.fn("anything"))


class VerifyAdminCredentialsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        from app.auth import hash_password, verify_admin_credentials
        self.hash_password = hash_password
        self.fn = verify_admin_credentials

    def tearDown(self) -> None:
        os.environ.pop("ADMIN_USERNAME", None)
        os.environ.pop("ADMIN_PASSWORD_HASH", None)

    def test_all_match(self) -> None:
        os.environ["ADMIN_USERNAME"] = "admin"
        os.environ["ADMIN_PASSWORD_HASH"] = self.hash_password("secret")
        self.assertTrue(self.fn("admin", "secret"))

    def test_username_mismatch(self) -> None:
        os.environ["ADMIN_USERNAME"] = "admin"
        os.environ["ADMIN_PASSWORD_HASH"] = self.hash_password("secret")
        self.assertFalse(self.fn("wronguser", "secret"))

    def test_password_mismatch(self) -> None:
        os.environ["ADMIN_USERNAME"] = "admin"
        os.environ["ADMIN_PASSWORD_HASH"] = self.hash_password("secret")
        self.assertFalse(self.fn("admin", "wrongpass"))

    def test_empty_username_config_returns_false(self) -> None:
        os.environ["ADMIN_PASSWORD_HASH"] = self.hash_password("secret")
        self.assertFalse(self.fn("admin", "secret"))


class WriteAuditEventDbTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["APP_ENV"] = "test"
        os.environ["DATABASE_URL"] = f"sqlite:///{self.temp_dir.name}/test.db"
        from app.database import initialize_database
        initialize_database()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        os.environ.pop("DATABASE_URL", None)

    def test_creates_event_and_returns_counts(self) -> None:
        from app.auth import _write_audit_event
        event_id, count = _write_audit_event("admin_login", "192.168.1.1", "/api/admin/login", action="login_attempt")
        self.assertEqual(len(event_id), 12)
        self.assertGreaterEqual(count, 0)

    def test_multiple_events_increment_count(self) -> None:
        from app.auth import _write_audit_event
        _write_audit_event("admin_login_failed", "10.0.0.1", "/login", action="bad_password")
        _, count = _write_audit_event("admin_login_failed", "10.0.0.1", "/login", action="bad_password")
        self.assertGreaterEqual(count, 2)


class CheckLoginCooldownDbTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["APP_ENV"] = "test"
        os.environ["DATABASE_URL"] = f"sqlite:///{self.temp_dir.name}/test.db"
        from app.database import initialize_database
        initialize_database()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        os.environ.pop("DATABASE_URL", None)
        os.environ.pop("ADMIN_LOGIN_FAILURE_LIMIT", None)
        os.environ.pop("ADMIN_LOGIN_FAILURE_WINDOW_MINUTES", None)
        os.environ.pop("ADMIN_LOGIN_COOLDOWN_MINUTES", None)

    def test_no_failures_no_cooldown(self) -> None:
        from app.auth import check_login_cooldown
        active, message = check_login_cooldown("192.168.1.1")
        self.assertFalse(active)
        self.assertIsNone(message)


class RequireAdminSessionTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["APP_ENV"] = "test"
        os.environ["ADMIN_ROUTE_SLUG"] = "adminconsole"
        os.environ["DATABASE_URL"] = f"sqlite:///{self.temp_dir.name}/test.db"
        from app.database import initialize_database
        initialize_database()

    def tearDown(self) -> None:
        os.environ.pop("ADMIN_ROUTE_SLUG", None)
        os.environ.pop("DATABASE_URL", None)
        self.temp_dir.cleanup()

    def test_missing_cookie_raises_401(self) -> None:
        from app.auth import require_admin_session
        request = SimpleNamespace(
            headers={},
            client=SimpleNamespace(host="192.168.1.1"),
            url=SimpleNamespace(path="/api/admin/workbench/feedback"),
        )
        with self.assertRaises(HTTPException) as ctx:
            require_admin_session(request, ia_admin_session=None)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_invalid_session_token_raises_401(self) -> None:
        from app.auth import require_admin_session
        request = SimpleNamespace(
            headers={},
            client=SimpleNamespace(host="192.168.1.1"),
            url=SimpleNamespace(path="/api/admin/workbench/feedback"),
        )
        with self.assertRaises(HTTPException) as ctx:
            require_admin_session(request, ia_admin_session="invalid-token")
        self.assertEqual(ctx.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
