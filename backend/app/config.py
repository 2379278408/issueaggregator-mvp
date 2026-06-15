from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_ADMIN_ROUTE_SLUG_PATTERN = re.compile(r"^[a-z0-9]{8,64}$")


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"{name} is required but not set")
    return value


def _split_csv_env(name: str) -> tuple[str, ...]:
    raw_value = os.getenv(name, "")
    values = [item.strip().rstrip("/") for item in raw_value.split(",") if item.strip()]
    return tuple(values)


def _load_env_file() -> None:
    if os.getenv("APP_ENV") == "test":
        return
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _default_database_url() -> str:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    raw_env = os.getenv("APP_ENV", "development").strip().lower()
    if raw_env in {"", "development", "dev", "local"}:
        filename = "issue_aggregator.dev.db"
    elif raw_env in {"production", "prod"}:
        filename = "issue_aggregator.db"
    else:
        normalized_env = "".join(character if character.isalnum() or character in {"-", "_"} else "-" for character in raw_env)
        filename = f"issue_aggregator.{normalized_env}.db"
    return f"sqlite:///{data_dir / filename}"


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    database_url: str
    api_base_path: str
    admin_api_namespace: str
    admin_api_token: str | None
    admin_route_slug: str
    admin_username: str | None
    admin_password_hash: str | None
    admin_session_secret: str | None
    admin_session_cookie_name: str
    admin_session_idle_minutes: int
    admin_session_max_hours: int
    admin_login_failure_limit: int
    admin_login_failure_window_minutes: int
    admin_login_cooldown_minutes: int
    enable_api_docs: bool
    github_token: str | None
    github_repo_owner: str | None
    github_repo_name: str | None
    ai_api_key: str | None
    ai_api_base_url: str | None
    ai_model: str | None
    rate_limit_per_hour: int
    related_id_rate_limit_window: int
    public_feedback_daily_ip_limit: int
    trust_proxy_headers: bool
    public_feedback_allowed_origins: tuple[str, ...]
    public_feedback_duplicate_window_minutes: int


def _validate_admin_route_slug(raw_slug: str) -> str:
    slug = raw_slug.strip()
    if not slug or not _ADMIN_ROUTE_SLUG_PATTERN.fullmatch(slug):
        raise SystemExit("ADMIN_ROUTE_SLUG must be 8-64 lowercase alphanumeric characters")
    return slug


def _production_required(name: str, raw_value: str | None) -> str:
    if not raw_value:
        raise SystemExit(f"{name} is required in production")
    return raw_value


def _validate_admin_security_settings(app_env: str, admin_username: str | None, admin_password_hash: str | None, admin_session_secret: str | None) -> None:
    if app_env in {"production", "prod"}:
        _production_required("ADMIN_USERNAME", admin_username)
        _production_required("ADMIN_PASSWORD_HASH", admin_password_hash)
        _production_required("ADMIN_SESSION_SECRET", admin_session_secret)


def get_settings() -> Settings:
    _load_env_file()
    app_env = os.getenv("APP_ENV", "development")
    enable_api_docs = os.getenv("ENABLE_API_DOCS", "false").strip().lower() in {"1", "true", "yes", "on"}
    admin_route_slug = _validate_admin_route_slug(os.getenv("ADMIN_ROUTE_SLUG", "adminconsole"))
    admin_username = os.getenv("ADMIN_USERNAME", "").strip() or None
    admin_password_hash = os.getenv("ADMIN_PASSWORD_HASH", "").strip() or None
    admin_session_secret = os.getenv("ADMIN_SESSION_SECRET", "").strip() or None
    _validate_admin_security_settings(app_env, admin_username, admin_password_hash, admin_session_secret)
    return Settings(
        app_name=os.getenv("APP_NAME", "Issue Aggregator API"),
        app_env=app_env,
        database_url=os.getenv("DATABASE_URL", _default_database_url()),
        api_base_path=os.getenv("API_BASE_PATH", "/api").rstrip("/"),
        admin_api_namespace=os.getenv("ADMIN_API_NAMESPACE", "workbench").strip() or "workbench",
        admin_api_token=os.getenv("ADMIN_API_TOKEN"),
        admin_route_slug=admin_route_slug,
        admin_username=admin_username,
        admin_password_hash=admin_password_hash,
        admin_session_secret=admin_session_secret,
        admin_session_cookie_name=os.getenv("ADMIN_SESSION_COOKIE_NAME", "ia_admin_session").strip(),
        admin_session_idle_minutes=int(os.getenv("ADMIN_SESSION_IDLE_MINUTES", "120")),
        admin_session_max_hours=int(os.getenv("ADMIN_SESSION_MAX_HOURS", "24")),
        admin_login_failure_limit=int(os.getenv("ADMIN_LOGIN_FAILURE_LIMIT", "5")),
        admin_login_failure_window_minutes=int(os.getenv("ADMIN_LOGIN_FAILURE_WINDOW_MINUTES", "15")),
        admin_login_cooldown_minutes=int(os.getenv("ADMIN_LOGIN_COOLDOWN_MINUTES", "30")),
        enable_api_docs=enable_api_docs,
        github_token=os.getenv("GITHUB_TOKEN"),
        github_repo_owner=os.getenv("GITHUB_REPO_OWNER"),
        github_repo_name=os.getenv("GITHUB_REPO_NAME"),
        ai_api_key=os.getenv("AI_API_KEY"),
        ai_api_base_url=os.getenv("AI_API_BASE_URL"),
        ai_model=os.getenv("AI_MODEL"),
        rate_limit_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "20")),
        related_id_rate_limit_window=int(os.getenv("RELATED_ID_RATE_LIMIT_WINDOW", "24")),
        public_feedback_daily_ip_limit=int(os.getenv("PUBLIC_FEEDBACK_DAILY_IP_LIMIT", "5")),
        trust_proxy_headers=os.getenv("TRUST_PROXY_HEADERS", "false").strip().lower() in {"1", "true", "yes", "on"},
        public_feedback_allowed_origins=_split_csv_env("PUBLIC_FEEDBACK_ALLOWED_ORIGINS"),
        public_feedback_duplicate_window_minutes=int(os.getenv("PUBLIC_FEEDBACK_DUPLICATE_WINDOW_MINUTES", "10")),
    )
