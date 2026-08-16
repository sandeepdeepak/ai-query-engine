from functools import lru_cache
from pathlib import Path
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_session
from app.security.access_store import (
    ApiAccessStore,
    LocalApiAccessStore,
    PostgresApiAccessStore,
)
from app.security.api_keys import ApiClient, ApiKeyRegistry
from app.security.rate_limit import InMemoryRateLimiter

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


@lru_cache
def get_api_key_registry() -> ApiKeyRegistry:
    return ApiKeyRegistry(Path(get_settings().public_api_keys_file))


@lru_cache
def get_rate_limiter() -> InMemoryRateLimiter:
    return InMemoryRateLimiter()


def get_api_access_store(
    session: Annotated[AsyncSession, Depends(get_session)],
    registry: Annotated[ApiKeyRegistry, Depends(get_api_key_registry)],
    limiter: Annotated[InMemoryRateLimiter, Depends(get_rate_limiter)],
) -> ApiAccessStore:
    if get_settings().public_api_access_backend == "postgres":
        return PostgresApiAccessStore(session)
    return LocalApiAccessStore(registry, limiter)


async def require_api_client(
    api_key: Annotated[str | None, Depends(api_key_header)],
    request: Request,
    store: Annotated[ApiAccessStore, Depends(get_api_access_store)],
) -> ApiClient:
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    client, retry_after, remaining = await store.authorize(api_key)
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    request.state.api_access_store = store
    request.state.rate_limit = client.requests_per_minute
    request.state.rate_limit_remaining = remaining
    if retry_after:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="API rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )
    return client


async def enforce_rate_limit(
    request: Request,
    client: Annotated[ApiClient, Depends(require_api_client)],
) -> ApiClient:
    return client
