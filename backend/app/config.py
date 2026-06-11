from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _default_database_url() -> str:
    data_dir = Path(__file__).resolve().parents[1] / "data"
    return f"sqlite:///{data_dir / 'issue_aggregator.db'}"


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_env: str
    database_url: str
    github_token: str | None
    github_repo_owner: str | None
    github_repo_name: str | None
    ai_api_key: str | None
    ai_api_base_url: str | None
    rate_limit_per_hour: int
    related_id_rate_limit_window: int


def get_settings() -> Settings:
    return Settings(
        app_name=os.getenv("APP_NAME", "Issue Aggregator API"),
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL", _default_database_url()),
        github_token=os.getenv("GITHUB_TOKEN"),
        github_repo_owner=os.getenv("GITHUB_REPO_OWNER"),
        github_repo_name=os.getenv("GITHUB_REPO_NAME"),
        ai_api_key=os.getenv("AI_API_KEY"),
        ai_api_base_url=os.getenv("AI_API_BASE_URL"),
        rate_limit_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "20")),
        related_id_rate_limit_window=int(os.getenv("RELATED_ID_RATE_LIMIT_WINDOW", "24")),
    )
