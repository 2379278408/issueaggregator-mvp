from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models import DraftBatchCreatePayload, DraftUpdatePayload, FeedbackCreatePayload, FeedbackStatus
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

router = APIRouter(prefix="/api", tags=["feedback"])
feedback_repository = FeedbackRepository()
submission_repository = SubmissionRepository()
draft_batch_service = DraftBatchService()
draft_integration_service = DraftIntegrationService()
draft_repository = DraftRepository()
draft_submission_service = DraftSubmissionService()


def _validate_pagination(page: int, page_size: int) -> None:
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(status_code=400, detail="Invalid pagination parameters")


@router.post("/feedback")
def create_feedback(payload: FeedbackCreatePayload) -> dict[str, object]:
    record = feedback_repository.create_feedback(payload)
    return success_response(
        {
            "id": record.id,
            "status": record.status.value,
            "created_at": record.created_at,
        }
    )


@router.get("/issues/submitted")
def list_submitted_issues(
    page: int = 1,
    page_size: int = 20,
) -> dict[str, object]:
    _validate_pagination(page, page_size)
    data = submission_repository.list_submitted_issues(page=page, page_size=page_size)
    return success_response(data)


@router.get("/issues/submitted/search")
def search_submitted_issues(
    related_id: str | None = None,
    type: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, object]:
    _validate_pagination(page, page_size)
    data = submission_repository.list_submitted_issues(
        page=page,
        page_size=page_size,
        related_id=related_id.strip() if related_id else None,
        issue_type=type.strip() if type else None,
        keyword=keyword,
    )
    return success_response(data)


@router.get("/feedback")
def list_feedback(
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, object]:
    _validate_pagination(page, page_size)

    parsed_status = FeedbackStatus(status) if status else None
    data = feedback_repository.list_feedback(status=parsed_status, page=page, page_size=page_size)
    return success_response(data)


@router.post("/draft-batches")
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


@router.post("/draft-batches/{batch_id}/integrate")
def integrate_draft_batch(batch_id: str) -> dict[str, object]:
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


@router.get("/drafts/{draft_id}")
def get_draft(draft_id: str) -> dict[str, object]:
    draft = draft_repository.get_draft(draft_id)
    if not draft:
        return error_response("DRAFT_BATCH_EMPTY", "Draft not found")
    return success_response(draft.model_dump(mode="json"))


@router.put("/drafts/{draft_id}")
def update_draft(draft_id: str, payload: DraftUpdatePayload) -> dict[str, object]:
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


@router.post("/drafts/{draft_id}/submit")
def submit_draft(draft_id: str) -> dict[str, object]:
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
