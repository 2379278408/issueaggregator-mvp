from __future__ import annotations

from re import fullmatch
from secrets import compare_digest

from fastapi import APIRouter, Depends, Header, HTTPException

from ..config import get_settings
from ..models import (
    BATCH_ID_PATTERN,
    DRAFT_ID_PATTERN,
    FEEDBACK_ID_PATTERN,
    FEEDBACK_TYPES,
    DraftBatchCreatePayload,
    DraftUpdatePayload,
    FeedbackCreatePayload,
    FeedbackStatus,
)
from ..repositories import (
    DraftBatchService,
    DraftIntegrationService,
    DraftRepository,
    DraftSubmissionService,
    FeedbackRepository,
    RepositoryError,
    SubmissionRepository,
)
from ..responses import error_response, success_response

settings = get_settings()
public_router = APIRouter(prefix=settings.api_base_path, tags=["feedback"])
feedback_repository = FeedbackRepository()
submission_repository = SubmissionRepository()
draft_batch_service = DraftBatchService()
draft_integration_service = DraftIntegrationService()
draft_repository = DraftRepository()
draft_submission_service = DraftSubmissionService()


def require_admin_token(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> None:
    if not settings.admin_api_token:
        raise HTTPException(status_code=503, detail="Admin API token is not configured")
    if not x_admin_token or not compare_digest(x_admin_token, settings.admin_api_token):
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


@public_router.post("/feedback")
def create_feedback(payload: FeedbackCreatePayload) -> dict[str, object]:
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


@admin_router.post("/draft-batches")
def create_draft_batch(payload: DraftBatchCreatePayload) -> dict[str, object]:
    try:
        batch = draft_batch_service.create_batch(payload.feedback_item_ids, payload.confirm_mixed_related_ids)
    except RepositoryError as exc:
        message = str(exc)
        if "explicit confirmation" in message:
            return error_response("MIXED_RELATED_ID_CONFIRM_REQUIRED", message)
        if "belongs to an active batch" in message:
            return error_response("FEEDBACK_ALREADY_GROUPED", message)
        return error_response("DRAFT_BATCH_EMPTY", message)

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
def integrate_draft_batch(batch_id: str) -> dict[str, object]:
    batch_id = _validate_resource_id(batch_id, BATCH_ID_PATTERN)
    try:
        draft = draft_integration_service.integrate_batch(batch_id)
    except RepositoryError as exc:
        message = str(exc)
        if "not found" in message:
            return error_response("DRAFT_BATCH_EMPTY", message)
        return error_response("AI_INTEGRATION_FAILED", message)

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
def update_draft(draft_id: str, payload: DraftUpdatePayload) -> dict[str, object]:
    draft_id = _validate_resource_id(draft_id, DRAFT_ID_PATTERN)
    draft = draft_repository.update_draft(draft_id, payload)
    if not draft:
        return error_response("DRAFT_BATCH_EMPTY", "Draft not found")
    return success_response(
        {
            "id": draft.id,
            "status": draft.status.value,
            "updated_at": draft.updated_at,
        }
    )


@admin_router.post("/drafts/{draft_id}/submit")
def submit_draft(draft_id: str) -> dict[str, object]:
    draft_id = _validate_resource_id(draft_id, DRAFT_ID_PATTERN)
    try:
        submission = draft_submission_service.submit_draft(draft_id)
    except RepositoryError as exc:
        message = str(exc)
        if "GITHUB_TOKEN" in message or "repository settings" in message:
            return error_response("TOKEN_MISSING", message)
        if "rate limit" in message:
            return error_response("RELATED_ID_RATE_LIMITED", message)
        if "Draft not found" in message:
            return error_response("GITHUB_SUBMIT_FAILED", message)
        return error_response("GITHUB_SUBMIT_FAILED", message)

    return success_response(
        {
            "draft_id": draft_id,
            "issue_number": submission.github_issue_number,
            "issue_url": submission.github_issue_url,
            "related_id": submission.related_id,
            "submitted_at": submission.submitted_at,
        }
    )
