from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from re import fullmatch
from typing import Literal
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

RELATED_ID_PATTERN = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
FEEDBACK_ID_PATTERN = r'^fb_[a-f0-9]{12}$'
BATCH_ID_PATTERN = r'^batch_[a-f0-9]{12}$'
DRAFT_ID_PATTERN = r'^draft_[a-f0-9]{12}$'
FeedbackType = Literal['bug', 'feature', 'enhancement', 'question']
FEEDBACK_TYPES = {'bug', 'feature', 'enhancement', 'question'}


class FeedbackStatus(str, Enum):
    PENDING = 'pending'
    GROUPED = 'grouped'
    SUBMITTED = 'submitted'


class DraftBatchStatus(str, Enum):
    CREATED = 'created'
    INTEGRATING = 'integrating'
    DRAFT_READY = 'draft_ready'
    APPROVED = 'approved'
    SUBMITTED = 'submitted'
    FAILED = 'failed'


class DraftStatus(str, Enum):
    DRAFT_READY = 'draft_ready'
    APPROVED = 'approved'
    SUBMITTED = 'submitted'
    FAILED = 'failed'


class FeedbackCreatePayload(BaseModel):
    type: FeedbackType
    related_id: str = Field(min_length=1, max_length=64)
    raw_content: str = Field(min_length=1, max_length=2000)
    expected_behavior: str | None = Field(default=None, max_length=1200)
    actual_behavior: str | None = Field(default=None, max_length=1200)
    page_url: str | None = None
    page_title: str | None = Field(default=None, max_length=200)
    environment_context: str | None = Field(default=None, max_length=500)

    @field_validator('related_id')
    @classmethod
    def validate_related_id(cls, value: str) -> str:
        normalized = value.strip()
        if not fullmatch(RELATED_ID_PATTERN, normalized):
            raise ValueError('related_id must use lowercase letters, numbers, and hyphens')
        return normalized

    @field_validator('raw_content')
    @classmethod
    def validate_raw_content(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError('raw_content cannot be empty')
        return normalized

    @field_validator('page_url')
    @classmethod
    def validate_page_url(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            return None

        parsed = urlsplit(normalized)
        if parsed.scheme and parsed.netloc:
            sanitized = urlunsplit((parsed.scheme, parsed.netloc, parsed.path or '/', '', ''))
        elif normalized.startswith('/'):
            sanitized = urlunsplit(('', '', parsed.path or '/', '', ''))
        else:
            sanitized = normalized.split('#', 1)[0].split('?', 1)[0]

        sanitized = sanitized.strip()
        if not sanitized:
            return None
        return sanitized[:1000]

    @field_validator('expected_behavior', 'actual_behavior', 'page_url', 'page_title', 'environment_context')
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class DraftBatchCreatePayload(BaseModel):
    feedback_item_ids: list[str] = Field(min_length=1, max_length=50)
    confirm_mixed_related_ids: bool = False

    @field_validator('feedback_item_ids')
    @classmethod
    def validate_feedback_item_ids(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value if item and item.strip()]
        if not normalized:
            raise ValueError('feedback_item_ids cannot be empty')
        if len(set(normalized)) != len(normalized):
            raise ValueError('feedback_item_ids cannot contain duplicates')
        return normalized


class DraftUpdatePayload(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    body_markdown: str = Field(min_length=1, max_length=12000)

    @field_validator('title', 'body_markdown')
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError('field cannot be empty')
        return normalized


class FeedbackRecord(BaseModel):
    id: str
    type: FeedbackType
    related_id: str
    raw_content: str
    expected_behavior: str | None
    actual_behavior: str | None
    page_url: str | None = None
    page_title: str | None = None
    environment_context: str | None = None
    status: FeedbackStatus
    created_at: str
    submitted_at: str | None


class SubmittedIssueRecord(BaseModel):
    issue_number: int
    title: str
    issue_url: str
    related_id: str
    type: FeedbackType
    submitted_at: str


class DraftBatchRecord(BaseModel):
    id: str
    status: DraftBatchStatus
    primary_related_id: str | None
    related_id_count: int
    integration_error: str | None
    created_at: str
    updated_at: str


class DraftBatchItemRecord(BaseModel):
    id: str
    batch_id: str
    feedback_item_id: str


class DraftRecord(BaseModel):
    id: str
    batch_id: str
    title: str
    body_markdown: str
    related_id_summary: str
    status: DraftStatus
    ai_model: str | None
    prompt_snapshot: str | None
    updated_at: str


class SubmissionRecord(BaseModel):
    id: str
    draft_id: str
    github_issue_number: int
    github_issue_url: str
    related_id: str
    github_state: str | None
    labels_snapshot: str | None
    response_status: int
    submitted_at: str
    error_summary: str | None


class PaginatedResult(BaseModel):
    items: list[dict]
    page: int
    page_size: int
    total: int


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def new_feedback_id() -> str:
    return f'fb_{uuid4().hex[:12]}'


def new_batch_id() -> str:
    return f'batch_{uuid4().hex[:12]}'


def new_batch_item_id() -> str:
    return f'dbi_{uuid4().hex[:12]}'


def new_draft_id() -> str:
    return f'draft_{uuid4().hex[:12]}'


def new_submission_id() -> str:
    return f'sub_{uuid4().hex[:12]}'


def new_session_token() -> str:
    return uuid4().hex + uuid4().hex


def new_login_attempt_id() -> str:
    return f'la_{uuid4().hex[:12]}'


class AdminLoginPayload(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)

    @field_validator('username', 'password')
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError('field cannot be empty')
        return normalized


class AdminLoginResult(BaseModel):
    success: bool
    session_id: str | None = None
    username: str | None = None
    session_expires_at: str | None = None


class AdminSessionStatus(BaseModel):
    authenticated: bool
    username: str | None = None
    session_expires_at: str | None = None
    idle_expires_at: str | None = None


class AdminSessionRecord(BaseModel):
    id: str
    session_token_hash: str
    username: str
    client_ip: str | None
    user_agent_summary: str | None
    created_at: str
    last_seen_at: str
    idle_expires_at: str
    absolute_expires_at: str
    revoked_at: str | None


class AdminLoginAttemptRecord(BaseModel):
    id: str
    username: str
    client_ip: str | None
    result: str
    reason: str | None
    created_at: str
