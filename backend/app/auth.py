from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from ipaddress import ip_address
from uuid import uuid4

import bcrypt
from fastapi import Request

from .config import get_settings
from .models import datetime_to_iso
from .repositories import AdminLoginAttemptRepository, AuditEventRepository


_AUDIT_WINDOW = timedelta(minutes=10)


def _normalize_client_ip(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip().lower()
    if not cleaned:
        return None
    return cleaned


def _parse_client_ip(candidate: str | None) -> ip_address | None:
    if not candidate:
        return None
    try:
        return ip_address(candidate)
    except ValueError:
        return None


def _resolve_client_ip(request: Request) -> str | None:
    settings = get_settings()
    forwarded_header = request.headers.get('x-forwarded-for')
    forwarded_raw = forwarded_header.split(',', 1)[0] if forwarded_header else None
    forwarded_ip = _parse_client_ip(_normalize_client_ip(forwarded_raw))

    if settings.trust_proxy_headers and forwarded_ip:
        return str(forwarded_ip)

    direct_ip = _normalize_client_ip(request.client.host if request.client else None)
    direct_peer = _parse_client_ip(direct_ip)
    if direct_peer and direct_peer.is_global:
        return direct_ip

    if (
        direct_peer
        and forwarded_ip
        and (direct_peer.is_private or direct_peer.is_loopback or direct_peer.is_link_local)
    ):
        return str(forwarded_ip)

    return None


def _write_audit_event(
    event_type: str, client_ip: str, path: str, *, action: str | None = None, resource_id: str | None = None
) -> tuple[str, int]:
    audit_repo = AuditEventRepository()
    event_id = uuid4().hex[:12]
    now = datetime.now(timezone.utc)
    since_iso = datetime_to_iso(now - _AUDIT_WINDOW)
    audit_repo.create_event(
        event_id=event_id,
        event_type=event_type,
        client_ip=client_ip,
        path=path,
        action=action,
        resource_id=resource_id,
    )
    recent_count = audit_repo.count_recent_events(event_type=event_type, client_ip=client_ip, since_iso=since_iso)
    return event_id, recent_count


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_admin_password(password: str) -> bool:
    settings = get_settings()
    stored = settings.admin_password_hash
    if not stored:
        return False
    if stored.startswith('$2'):
        return bcrypt.checkpw(password.encode(), stored.encode())
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    return hmac.compare_digest(password_hash, stored)


def verify_admin_credentials(username: str, password: str) -> bool:
    settings = get_settings()
    if not settings.admin_username:
        return False
    if not hmac.compare_digest(username, settings.admin_username):
        return False
    return verify_admin_password(password)


def check_login_cooldown(client_ip: str) -> tuple[bool, str | None]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    window_since = datetime_to_iso(now - timedelta(minutes=settings.admin_login_failure_window_minutes))

    attempt_repo = AdminLoginAttemptRepository()
    failure_count = attempt_repo.count_recent_failures(client_ip=client_ip, since_iso=window_since)

    if failure_count >= settings.admin_login_failure_limit:
        cooldown_since = datetime_to_iso(now - timedelta(minutes=settings.admin_login_cooldown_minutes))
        last_attempt = attempt_repo.last_attempt_after(client_ip=client_ip, since_iso=cooldown_since)
        if last_attempt is not None and last_attempt.result in (
            AdminLoginAttemptRepository.LOGIN_RESULT_FAILURE,
            AdminLoginAttemptRepository.LOGIN_RESULT_COOLDOWN,
        ):
            remaining_seconds = int(
                (now - datetime.fromisoformat(last_attempt.created_at.replace('Z', '+00:00'))).total_seconds()
            )
            remaining = max(0, (settings.admin_login_cooldown_minutes * 60) - remaining_seconds)
            if remaining > 0:
                return True, f'Login cooldown active, try again in {remaining // 60}m {remaining % 60}s'

    return False, None
