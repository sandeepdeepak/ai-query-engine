from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.api.routes import public
from app.core.config import get_settings
from app.db.session import close_database

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await close_database()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Natural language to safe SQL to structured data.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(settings.frontend_origin).rstrip("/")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix=settings.api_v1_prefix)
app.include_router(public.router, prefix="/public/v1", tags=["public-api"])


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = f"req_{uuid4().hex}"
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(HTTPException)
async def public_http_error(request: Request, exc: HTTPException):
    if not request.url.path.startswith("/public/"):
        return await http_exception_handler(request, exc)
    codes = {
        401: "invalid_api_key",
        403: "forbidden",
        422: "unsafe_or_invalid_query",
        429: "rate_limit_exceeded",
        502: "upstream_failure",
        503: "service_unavailable",
    }
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        headers=exc.headers,
        content={
            "error": {
                "code": codes.get(exc.status_code, "request_failed"),
                "message": str(exc.detail),
                "request_id": request_id,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def public_validation_error(request: Request, exc: RequestValidationError):
    if not request.url.path.startswith("/public/"):
        return JSONResponse(status_code=422, content={"detail": exc.errors()})
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "invalid_request",
                "message": "Request payload validation failed",
                "request_id": getattr(request.state, "request_id", None),
            }
        },
    )


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs"}
