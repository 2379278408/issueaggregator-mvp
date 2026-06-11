from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .config import get_settings
from .database import initialize_database
from .responses import error_response
from .routers.feedback import router as feedback_router
from .routers.health import router as health_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_database()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(health_router)
app.include_router(feedback_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0]
    return JSONResponse(
        status_code=400,
        content=error_response("VALIDATION_ERROR", first_error.get("msg", "Request validation failed")),
    )


@app.get("/")
def root() -> dict[str, object]:
    return error_response("NOT_IMPLEMENTED", "API root is reserved. Use /api endpoints.")
