from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from ipaddress import IPv4Address, IPv6Address, ip_address
from re import fullmatch
from secrets import compare_digest
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response

from ..auth import (
    _resolve_client_ip,
    _write_audit_event,
    check_login_cooldown,
    hash_session_token,
    require_admin_session,
    verify_admin_credentials,
)
from ..config import get_settings
from ..models import (
    AdminLoginPayload,
    AdminSessionStatus,
    BATCH_ID_PATTERN,
    DRAFT_ID_PATTERN,
    FEEDBACK_ID_PATTERN,
    FEEDBACK_TYPES,
    DraftBatchCreatePayload,
    DraftUpdatePayload,
    FeedbackCreatePayload,
    FeedbackStatus,
    new_session_token,
)
from ..repositories import (
    AdminLoginAttemptRepository,
    AdminSessionRepository,
    DraftBatchService,
    DraftIntegrationService,
    DraftRepository,
    DraftSubmissionService,
    FeedbackRepository,
    PublicFeedbackRateLimitRepository,
    RepositoryError,
    SubmissionRepository,
    AuditEventRepository,
)
from ..responses import error_response, success_response

settings = get_settings()
logger = logging.getLogger(__name__)
_AUDIT_WINDOW = timedelta(minutes=10)
public_router = APIRouter(prefix=settings.api_base_path, tags=["feedback"])
feedback_repository = FeedbackRepository()
feedback_rate_limit_repository = PublicFeedbackRateLimitRepository()
audit_event_repository = AuditEventRepository()
submission_repository = SubmissionRepository()
draft_batch_service = DraftBatchService()
draft_integration_service = DraftIntegrationService()
draft_repository = DraftRepository()
draft_submission_service = DraftSubmissionService()
admin_session_repository = AdminSessionRepository()
admin_login_attempt_repository = AdminLoginAttemptRepository()


def _normalized_origin_value(value: str | None) -> str | None:
    normalized = _normalize_query(value, max_length=255)
    if not normalized:
        return None
    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"}:
        raise HTTPException(status_code=400, detail="Invalid origin header")
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def _request_origin(request: Request) -> str:
    if settings.trust_proxy_headers:
        forwarded_proto = _normalize_query(request.headers.get("x-forwarded-proto"), max_length=16)
        forwarded_host = _normalize_query(request.headers.get("x-forwarded-host"), max_length=255)
        if forwarded_proto in {"http", "https"} and forwarded_host:
            return f"{forwarded_proto}://{forwarded_host}".rstrip("/")
    return str(request.base_url).rstrip("/")


def _request_origin_candidates(request: Request, request_origin: str) -> tuple[str, ...]:
    allowed_origins = {_request_origin(request)}
    host = _normalize_query(request.headers.get("host"), max_length=255)
    request_origin_parts = urlsplit(request_origin)
    if host and request_origin_parts.scheme in {"http", "https"}:
        allowed_origins.add(f"{request_origin_parts.scheme}://{host}".rstrip("/"))
    return tuple(allowed_origins)


def _enforce_public_feedback_origin(request: Request) -> None:
    request_origin = _normalized_origin_value(request.headers.get("origin"))
    if request_origin is None:
        return

    allowed_origins = settings.public_feedback_allowed_origins or _request_origin_candidates(request, request_origin)
    if request_origin not in allowed_origins:
        raise HTTPException(status_code=403, detail="Origin is not allowed")


def _record_audit_event(event_type: str, client_ip: str, path: str, *, action: str | None = None, resource_id: str | None = None) -> tuple[str, int]:
    event_id = uuid4().hex[:12]
    now = datetime.now(timezone.utc)
    since_iso = (now - _AUDIT_WINDOW).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    audit_event_repository.create_event(
        event_id=event_id,
        event_type=event_type,
        client_ip=client_ip,
        path=path,
        action=action,
        resource_id=resource_id,
    )
    recent_count = audit_event_repository.count_recent_events(event_type=event_type, client_ip=client_ip, since_iso=since_iso)
    return event_id, recent_count


def _log_admin_action(request: Request, *, action: str, resource_id: str | None = None) -> None:
    client_ip = _client_ip(request) or "unknown"
    event_id, recent_count = _record_audit_event(
        "admin_action_succeeded",
        client_ip,
        request.url.path,
        action=action,
        resource_id=resource_id,
    )
    logger.info(
        "admin_action_succeeded event_id=%s path=%s client_ip=%s action=%s resource_id=%s recent_count=%s",
        event_id,
        request.url.path,
        client_ip,
        action,
        resource_id or "-",
        recent_count,
    )


session_router = APIRouter(
    prefix=f"{settings.api_base_path}/admin/{settings.admin_api_namespace}/session",
    tags=["admin-session"],
)


@session_router.post("/login")
def admin_login(payload: AdminLoginPayload, request: Request, response: Response) -> dict[str, object]:
    client_ip = _resolve_client_ip(request) or "unknown"
    path = request.url.path

    on_cooldown, cooldown_reason = check_login_cooldown(client_ip)
    if on_cooldown:
        admin_login_attempt_repository.record_attempt(
            username=payload.username,
            client_ip=client_ip,
            result=AdminLoginAttemptRepository.LOGIN_RESULT_COOLDOWN,
            reason=cooldown_reason,
        )
        _write_audit_event("admin_auth_failed", client_ip, path, action="login_cooldown")
        return error_response("ADMIN_LOGIN_COOLDOWN_ACTIVE", cooldown_reason or "Login cooldown active")

    if not verify_admin_credentials(payload.username, payload.password):
        admin_login_attempt_repository.record_attempt(
            username=payload.username,
            client_ip=client_ip,
            result=AdminLoginAttemptRepository.LOGIN_RESULT_FAILURE,
            reason="invalid_credentials",
        )
        _write_audit_event("admin_auth_failed", client_ip, path, action="invalid_credentials")
        return error_response("AUTH_INVALID_CREDENTIALS", "Invalid username or password")

    settings = get_settings()
    session_token = new_session_token()
    session_token_hash = hash_session_token(session_token)
    user_agent_summary = _normalize_query(request.headers.get("user-agent", ""), max_length=255)

    session = admin_session_repository.create_session(
        session_token_hash=session_token_hash,
        username=settings.admin_username or payload.username,
        client_ip=client_ip,
        user_agent_summary=user_agent_summary,
    )

    admin_login_attempt_repository.record_attempt(
        username=payload.username,
        client_ip=client_ip,
        result=AdminLoginAttemptRepository.LOGIN_RESULT_SUCCESS,
    )
    _write_audit_event("admin_auth_succeeded", client_ip, path, action="login", resource_id=session.id)

    response.set_cookie(
        key=settings.admin_session_cookie_name,
        value=session_token,
        httponly=True,
        secure=settings.app_env in {"production", "prod"},
        samesite="strict",
        path=f"{settings.api_base_path}/admin",
        max_age=settings.admin_session_max_hours * 3600,
    )

    return success_response(
        {
            "username": session.username,
            "session_expires_at": session.absolute_expires_at,
            "idle_expires_at": session.idle_expires_at,
        }
    )


@session_router.get("/me")
def admin_session_me(request: Request) -> dict[str, object]:
    settings = get_settings()
    session_token = request.cookies.get(settings.admin_session_cookie_name)

    if not session_token:
        return success_response(AdminSessionStatus(authenticated=False).model_dump())

    session_token_hash = hash_session_token(session_token)
    session = admin_session_repository.find_active_session(session_token_hash)

    if session is None:
        return success_response(AdminSessionStatus(authenticated=False).model_dump())

    admin_session_repository.touch_session(session_token_hash)
    status = AdminSessionStatus(
        authenticated=True,
        username=session.username,
        session_expires_at=session.absolute_expires_at,
        idle_expires_at=session.idle_expires_at,
    )
    return success_response(status.model_dump())


@session_router.post("/logout")
def admin_logout(request: Request, response: Response) -> dict[str, object]:
    settings = get_settings()
    session_token = request.cookies.get(settings.admin_session_cookie_name)
    client_ip = _resolve_client_ip(request) or "unknown"

    if session_token:
        session_token_hash = hash_session_token(session_token)
        session = admin_session_repository.find_by_token_hash(session_token_hash)
        if session and not session.revoked_at:
            admin_session_repository.revoke_session(session_token_hash)
            _write_audit_event("admin_session_revoked", client_ip, request.url.path, action="logout", resource_id=session.id)

    response.delete_cookie(
        key=settings.admin_session_cookie_name,
        path=f"{settings.api_base_path}/admin",
    )
    return success_response({"status": "logged_out"})


def require_admin_token(request: Request, x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> None:
    client_ip = _client_ip(request) or "unknown"
    path = request.url.path

    cookies = getattr(request, "cookies", {})
    session_token = cookies.get(settings.admin_session_cookie_name) if isinstance(cookies, dict) else None
    if session_token:
        session_token_hash = hash_session_token(session_token)
        session = admin_session_repository.find_active_session(session_token_hash)
        if session is not None:
            admin_session_repository.touch_session(session_token_hash)
            return

    if settings.admin_api_token and x_admin_token:
        if compare_digest(x_admin_token, settings.admin_api_token):
            return

    if not settings.admin_api_token and not settings.admin_password_hash:
        event_id, recent_count = _record_audit_event("admin_auth_failed", client_ip, path)
        logger.warning(
            "admin_auth_failed event_id=%s path=%s client_ip=%s reason=token_not_configured recent_count=%s",
            event_id,
            path,
            client_ip,
            recent_count,
        )
        raise HTTPException(status_code=503, detail="Admin API token is not configured")

    event_id, recent_count = _record_audit_event("admin_auth_failed", client_ip, path)
    logger.warning(
        "admin_auth_failed event_id=%s path=%s client_ip=%s reason=invalid_token recent_count=%s",
        event_id,
        path,
        client_ip,
        recent_count,
    )
    raise HTTPException(status_code=401, detail="Invalid admin token")


admin_router = APIRouter(
    prefix=f"{settings.api_base_path}/admin/{settings.admin_api_namespace}",
    tags=["admin"],
    dependencies=[Depends(require_admin_token)],
)


def _validate_pagination(page: int, page_size: int) -> None:
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail="Invalid pagination parameters")


def _validate_resource_id(resource_id: str, pattern: str) -> str:
    normalized = resource_id.strip()
    if not fullmatch(pattern, normalized):
        raise HTTPException(status_code=404, detail="Not found")
    return normalized


def _normalize_query(value: str | None, *, max_length: int = 120) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > max_length:
        raise HTTPException(status_code=400, detail="Query parameter is too long")
    return normalized


def _normalize_feedback_type(value: str | None) -> str | None:
    normalized = _normalize_query(value, max_length=32)
    if normalized and normalized not in FEEDBACK_TYPES:
        raise HTTPException(status_code=400, detail="Invalid feedback type")
    return normalized


def _normalize_audit_event_type(value: str | None) -> str | None:
    normalized = _normalize_query(value, max_length=64)
    if normalized and normalized not in {"admin_auth_failed", "admin_auth_succeeded", "admin_action_succeeded", "admin_session_revoked"}:
        raise HTTPException(status_code=400, detail="Invalid audit event type")
    return normalized


def _normalize_audit_time_range(value: str | None) -> str | None:
    normalized = _normalize_query(value, max_length=16)
    if normalized and normalized not in {"10m", "1h", "24h", "all"}:
        raise HTTPException(status_code=400, detail="Invalid audit time range")
    return normalized


def _audit_since_iso(time_range: str | None) -> str | None:
    if time_range in {None, "all"}:
        return None
    now = datetime.now(timezone.utc)
    if time_range == "10m":
        since = now - timedelta(minutes=10)
    elif time_range == "1h":
        since = now - timedelta(hours=1)
    else:
        since = now - timedelta(hours=24)
    return since.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_client_ip(value: str | None) -> str | None:
    parsed_ip = _parse_client_ip(value)
    return str(parsed_ip) if parsed_ip else None


def _parse_client_ip(value: str | None) -> IPv4Address | IPv6Address | None:
    if not value:
        return None
    candidate = value.strip()
    if not candidate:
        return None
    try:
        return ip_address(candidate)
    except ValueError:
        return None


def _client_ip(request: Request) -> str | None:
    forwarded_header = request.headers.get("x-forwarded-for")
    forwarded_ip = _normalize_client_ip(forwarded_header.split(",", 1)[0]) if forwarded_header else None

    if settings.trust_proxy_headers and forwarded_ip:
        return forwarded_ip

    direct_ip = _normalize_client_ip(request.client.host if request.client else None)
    if direct_ip and _parse_client_ip(direct_ip).is_global:
        return direct_ip

    direct_peer = _parse_client_ip(direct_ip)
    if direct_peer and forwarded_ip and (direct_peer.is_private or direct_peer.is_loopback or direct_peer.is_link_local):
        return forwarded_ip

    return None


@public_router.post("/feedback")
def create_feedback(
    payload: FeedbackCreatePayload,
    request: Request,
    client_ip: str | None = Depends(_client_ip),
) -> dict[str, object]:
    _enforce_public_feedback_origin(request)
    duplicate_window_start = (
        datetime.now(timezone.utc) - timedelta(minutes=settings.public_feedback_duplicate_window_minutes)
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if feedback_repository.count_recent_duplicate_feedback(payload, since_iso=duplicate_window_start) > 0:
        return error_response(
            "FEEDBACK_DUPLICATE_CONTENT",
            f"相同反馈内容在 {settings.public_feedback_duplicate_window_minutes} 分钟内已提交，请避免重复提交。",
        )
    if isinstance(client_ip, str) and client_ip:
        if not feedback_rate_limit_repository.consume_daily_quota(
            ip_address=client_ip,
            limit=settings.public_feedback_daily_ip_limit,
        ):
            return error_response(
                "FEEDBACK_DAILY_IP_LIMIT_REACHED",
                f"同一 IP 每天最多提交 {settings.public_feedback_daily_ip_limit} 次反馈。",
            )
    elif client_ip is None:
        pass
    else:
        if not feedback_rate_limit_repository.consume_daily_quota(
            ip_address="local-test-client",
            limit=settings.public_feedback_daily_ip_limit,
        ):
            return error_response(
                "FEEDBACK_DAILY_IP_LIMIT_REACHED",
                f"同一 IP 每天最多提交 {settings.public_feedback_daily_ip_limit} 次反馈。",
            )
    record = feedback_repository.create_feedback(payload)
    return success_response(
        {
            "id": record.id,
            "status": record.status.value,
            "created_at": record.created_at,
        }
    )


@public_router.get("/issues/submitted")
def list_submitted_issues(
    page: int = 1,
    page_size: int = 20,
) -> dict[str, object]:
    _validate_pagination(page, page_size)
    data = submission_repository.list_submitted_issues(page=page, page_size=page_size)
    return success_response(data)


@public_router.get("/issues/submitted/search")
def search_submitted_issues(
    related_id: str | None = None,
    type: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, object]:
    _validate_pagination(page, page_size)
    normalized_related_id = _normalize_query(related_id, max_length=64)
    normalized_type = _normalize_feedback_type(type)
    normalized_keyword = _normalize_query(keyword, max_length=120)
    data = submission_repository.list_submitted_issues(
        page=page,
        page_size=page_size,
        related_id=normalized_related_id,
        issue_type=normalized_type,
        keyword=normalized_keyword,
    )
    return success_response(data)


@admin_router.get("/feedback")
def list_feedback(
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, object]:
    _validate_pagination(page, page_size)

    normalized_status = _normalize_query(status, max_length=32)
    try:
        parsed_status = FeedbackStatus(normalized_status) if normalized_status else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid feedback status") from exc
    data = feedback_repository.list_feedback(status=parsed_status, page=page, page_size=page_size)
    return success_response(data)


@admin_router.get("/audit-events")
def list_audit_events(
    event_type: str | None = None,
    keyword: str | None = None,
    time_range: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, object]:
    _validate_pagination(page, page_size)
    normalized_event_type = _normalize_audit_event_type(event_type)
    normalized_keyword = _normalize_query(keyword, max_length=120)
    normalized_time_range = _normalize_audit_time_range(time_range)
    data = audit_event_repository.list_events(
        event_type=normalized_event_type,
        keyword=normalized_keyword,
        since_iso=_audit_since_iso(normalized_time_range),
        page=page,
        page_size=page_size,
    )
    return success_response(data)


@admin_router.post("/draft-batches")
def create_draft_batch(payload: DraftBatchCreatePayload, request: Request) -> dict[str, object]:
    try:
        batch = draft_batch_service.create_batch(payload.feedback_item_ids, payload.confirm_mixed_related_ids)
    except RepositoryError as exc:
        message = str(exc)
        if "explicit confirmation" in message:
            return error_response("MIXED_RELATED_ID_CONFIRM_REQUIRED", message)
        if "belongs to an active batch" in message:
            return error_response("FEEDBACK_ALREADY_GROUPED", message)
        return error_response("DRAFT_BATCH_EMPTY", message)

    _log_admin_action(request, action="create_draft_batch", resource_id=batch.id)
    return success_response(
        {
            "id": batch.id,
            "status": batch.status.value,
            "primary_related_id": batch.primary_related_id,
            "related_id_count": batch.related_id_count,
            "created_at": batch.created_at,
        }
    )


@admin_router.post("/draft-batches/{batch_id}/integrate")
def integrate_draft_batch(batch_id: str, request: Request) -> dict[str, object]:
    batch_id = _validate_resource_id(batch_id, BATCH_ID_PATTERN)
    try:
        draft = draft_integration_service.integrate_batch(batch_id)
    except RepositoryError as exc:
        message = str(exc)
        if "not found" in message:
            return error_response("DRAFT_BATCH_EMPTY", message)
        return error_response("AI_INTEGRATION_FAILED", message)

    _log_admin_action(request, action="integrate_draft_batch", resource_id=draft.id)
    return success_response(
        {
            "batch_id": batch_id,
            "draft_id": draft.id,
            "status": draft.status.value,
        }
    )


@admin_router.get("/drafts/{draft_id}")
def get_draft(draft_id: str) -> dict[str, object]:
    draft_id = _validate_resource_id(draft_id, DRAFT_ID_PATTERN)
    draft = draft_repository.get_draft(draft_id)
    if not draft:
        return error_response("DRAFT_BATCH_EMPTY", "Draft not found")
    return success_response(draft.model_dump(mode="json"))


@admin_router.put("/drafts/{draft_id}")
def update_draft(draft_id: str, payload: DraftUpdatePayload, request: Request) -> dict[str, object]:
    draft_id = _validate_resource_id(draft_id, DRAFT_ID_PATTERN)
    draft = draft_repository.update_draft(draft_id, payload)
    if not draft:
        return error_response("DRAFT_BATCH_EMPTY", "Draft not found")
    _log_admin_action(request, action="update_draft", resource_id=draft.id)
    return success_response(
        {
            "id": draft.id,
            "status": draft.status.value,
            "updated_at": draft.updated_at,
        }
    )


@admin_router.post("/drafts/{draft_id}/submit")
def submit_draft(draft_id: str, request: Request) -> dict[str, object]:
    draft_id = _validate_resource_id(draft_id, DRAFT_ID_PATTERN)
    try:
        submission = draft_submission_service.submit_draft(draft_id)
    except RepositoryError as exc:
        message = str(exc)
        if "GITHUB_TOKEN" in message or "repository settings" in message:
            return error_response("TOKEN_MISSING", message)
        if "safe submission limit" in message or "sensitive credential-like content" in message:
            return error_response("DRAFT_CONTENT_REJECTED", message)
        if "rate limit" in message:
            return error_response("RELATED_ID_RATE_LIMITED", message)
        if "Draft not found" in message:
            return error_response("GITHUB_SUBMIT_FAILED", message)
        return error_response("GITHUB_SUBMIT_FAILED", message)

    _log_admin_action(request, action="submit_draft", resource_id=submission.id)
    return success_response(
        {
            "draft_id": draft_id,
            "issue_number": submission.github_issue_number,
            "issue_url": submission.github_issue_url,
            "related_id": submission.related_id,
            "submitted_at": submission.submitted_at,
        }
    )
