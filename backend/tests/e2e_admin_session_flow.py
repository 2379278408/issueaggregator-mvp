import hashlib
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    temp_dir = tempfile.TemporaryDirectory()
    os.environ['APP_ENV'] = 'test'
    os.environ['DATABASE_URL'] = f'sqlite:///{temp_dir.name}/e2e-admin-session.db'
    os.environ['ADMIN_USERNAME'] = 'admin'
    os.environ['ADMIN_PASSWORD_HASH'] = hashlib.sha256('secret-pass'.encode()).hexdigest()
    os.environ['TRUST_PROXY_HEADERS'] = 'true'
    os.environ['ADMIN_LOGIN_FAILURE_LIMIT'] = '2'
    os.environ['ADMIN_LOGIN_FAILURE_WINDOW_MINUTES'] = '15'
    os.environ['ADMIN_LOGIN_COOLDOWN_MINUTES'] = '30'

    from fastapi.testclient import TestClient

    from app.database import initialize_database
    from app.main import app

    initialize_database()
    client = TestClient(app)
    login_headers = {
        'X-Forwarded-For': '203.0.113.18',
        'Host': 'testserver',
    }

    try:
        first_failure = client.post(
            '/api/admin/workbench/session/login',
            headers=login_headers,
            json={'username': 'admin', 'password': 'wrong-pass'},
        )
        assert first_failure.status_code == 200, first_failure.text
        assert first_failure.json()['error_code'] == 'AUTH_INVALID_CREDENTIALS', first_failure.text

        second_failure = client.post(
            '/api/admin/workbench/session/login',
            headers=login_headers,
            json={'username': 'admin', 'password': 'wrong-pass'},
        )
        assert second_failure.status_code == 200, second_failure.text
        assert second_failure.json()['error_code'] == 'AUTH_INVALID_CREDENTIALS', second_failure.text

        cooldown = client.post(
            '/api/admin/workbench/session/login',
            headers=login_headers,
            json={'username': 'admin', 'password': 'secret-pass'},
        )
        assert cooldown.status_code == 200, cooldown.text
        assert cooldown.json()['error_code'] == 'ADMIN_LOGIN_COOLDOWN_ACTIVE', cooldown.text

        client.cookies.clear()
        success_login = client.post(
            '/api/admin/workbench/session/login',
            headers={'Host': 'testserver'},
            json={'username': 'admin', 'password': 'secret-pass'},
        )
        assert success_login.status_code == 200, success_login.text
        success_payload = success_login.json()
        assert success_payload['success'] is True, success_login.text
        assert success_payload['data']['username'] == 'admin', success_login.text

        session_me = client.get('/api/admin/workbench/session/me')
        assert session_me.status_code == 200, session_me.text
        assert session_me.json()['data']['authenticated'] is True, session_me.text

        protected = client.get('/api/admin/workbench/feedback?status=pending')
        assert protected.status_code == 200, protected.text

        logout = client.post('/api/admin/workbench/session/logout')
        assert logout.status_code == 200, logout.text
        assert logout.json()['data']['status'] == 'logged_out', logout.text

        session_me_after_logout = client.get('/api/admin/workbench/session/me')
        assert session_me_after_logout.status_code == 200, session_me_after_logout.text
        assert session_me_after_logout.json()['data']['authenticated'] is False, session_me_after_logout.text

        protected_after_logout = client.get('/api/admin/workbench/feedback?status=pending')
        assert protected_after_logout.status_code == 401, protected_after_logout.text

        print('ADMIN_SESSION_FLOW_E2E_OK')
    finally:
        client.close()
        temp_dir.cleanup()
        for key in [
            'APP_ENV',
            'DATABASE_URL',
            'ADMIN_USERNAME',
            'ADMIN_PASSWORD_HASH',
            'TRUST_PROXY_HEADERS',
            'ADMIN_LOGIN_FAILURE_LIMIT',
            'ADMIN_LOGIN_FAILURE_WINDOW_MINUTES',
            'ADMIN_LOGIN_COOLDOWN_MINUTES',
        ]:
            os.environ.pop(key, None)


if __name__ == '__main__':
    main()
