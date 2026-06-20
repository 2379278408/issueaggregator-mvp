from __future__ import annotations

from fastapi import APIRouter

from ..config import get_settings
from ..responses import success_response

settings = get_settings()
router = APIRouter(prefix=settings.api_base_path, tags=['health'])


@router.get('/health')
def health_check() -> dict[str, object]:
    return success_response(
        {
            'status': 'ok',
            'service': settings.app_name,
            'environment': settings.app_env,
        }
    )
