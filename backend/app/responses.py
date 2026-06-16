from __future__ import annotations

from typing import Any


def success_response(data: Any) -> dict[str, Any]:
    return {'success': True, 'data': data}


def error_response(error_code: str, message: str) -> dict[str, Any]:
    return {'success': False, 'error_code': error_code, 'message': message}
