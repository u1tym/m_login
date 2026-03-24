from __future__ import annotations

import json
import time
import traceback
from uuid import uuid4

from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .logging_utils import format_payload, setup_logging
from .routers import auth

settings = get_settings()
logger = setup_logging()

app = FastAPI(
    title="Auth API",
    description="JWT + HttpOnly Cookie による認証 API（/api/auth 向け）",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.middleware("http")
async def access_log_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    request_id = uuid4().hex[:12]
    request.state.request_id = request_id
    start = time.perf_counter()

    body_payload: object | None = None
    raw_body = await request.body()
    if raw_body:
        try:
            body_payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            body_payload = {"raw_body": raw_body[:1024].decode("utf-8", errors="replace")}

    request_params = {
        "path_params": request.path_params,
        "query_params": dict(request.query_params),
        "body": body_payload,
    }

    logger.info(
        "[%s] request method=%s path=%s client=%s params=%s",
        request_id,
        request.method,
        request.url.path,
        request.client.host if request.client else "unknown",
        format_payload(request_params),
    )

    try:
        response = await call_next(request)
    except Exception as exc:  # noqa: BLE001
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.error(
            "[%s] error method=%s path=%s elapsed_ms=%s error=%s traceback=%s",
            request_id,
            request.method,
            request.url.path,
            elapsed_ms,
            repr(exc),
            traceback.format_exc(),
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
        )

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "[%s] response method=%s path=%s status=%s elapsed_ms=%s",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        "[%s] http_error method=%s path=%s status=%s detail=%s",
        request_id,
        request.method,
        request.url.path,
        exc.status_code,
        format_payload(exc.detail),
    )
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(
        "[%s] validation_error method=%s path=%s errors=%s",
        request_id,
        request.method,
        request.url.path,
        format_payload(exc.errors()),
    )
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
