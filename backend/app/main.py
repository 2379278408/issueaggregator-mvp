from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import initialize_database
from .responses import error_response
from .routers.feedback import admin_router, public_router, session_router
from .routers.health import router as health_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    docs_url='/docs' if settings.enable_api_docs else None,
    redoc_url='/redoc' if settings.enable_api_docs else None,
    openapi_url='/openapi.json' if settings.enable_api_docs else None,
)
app.include_router(health_router)
app.include_router(public_router)
app.include_router(session_router)
app.include_router(admin_router)


@app.middleware('http')
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
    response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'
    response.headers['Content-Security-Policy'] = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    if request.url.path.startswith(settings.api_base_path):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0]
    return JSONResponse(
        status_code=400,
        content=error_response('VALIDATION_ERROR', first_error.get('msg', 'Request validation failed')),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else 'Request failed'
    error_code = 'NOT_FOUND' if exc.status_code == 404 else 'REQUEST_ERROR'
    return JSONResponse(status_code=exc.status_code, content=error_response(error_code, message))


@app.get('/')
def root() -> JSONResponse:
    return JSONResponse(status_code=404, content=error_response('NOT_FOUND', 'Not found'))
