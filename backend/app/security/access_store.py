import hashlib
import math
from datetime import UTC, datetime, timedelta
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.security.api_keys import ApiClient, ApiKeyRegistry
from app.security.rate_limit import InMemoryRateLimiter


class ApiAccessStore(Protocol):
    async def authorize(self, api_key: str) -> tuple[ApiClient | None, int, int]: ...

    async def record_usage(
        self,
        *,
        client_id: str,
        request_id: str,
        question_hash: str,
        status_code: int,
        row_count: int,
        duration_ms: float,
    ) -> None: ...


class LocalApiAccessStore:
    def __init__(self, registry: ApiKeyRegistry, limiter: InMemoryRateLimiter) -> None:
        self.registry = registry
        self.limiter = limiter

    async def authorize(self, api_key: str) -> tuple[ApiClient | None, int, int]:
        client = self.registry.authenticate(api_key)
        if client is None:
            return None, 0, 0
        allowed, retry_after, remaining = await self.limiter.check(
            client.id, limit=client.requests_per_minute
        )
        return client, retry_after if not allowed else 0, remaining

    async def record_usage(self, **_: object) -> None:
        return None


class PostgresApiAccessStore:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def authorize(self, api_key: str) -> tuple[ApiClient | None, int, int]:
        key_hash = ApiKeyRegistry.hash_key(api_key)
        result = await self.session.execute(
            text(
                """
                select id, name, key_prefix, key_hash, active, requests_per_minute, created_at
                from api_private.api_clients
                where key_hash = :key_hash and active = true
                """
            ),
            {"key_hash": key_hash},
        )
        row = result.mappings().one_or_none()
        if row is None:
            await self.session.rollback()
            return None, 0, 0

        client = ApiClient.model_validate(dict(row))
        now = datetime.now(UTC)
        window_start = now.replace(second=0, microsecond=0)
        counter = await self.session.execute(
            text(
                """
                insert into api_private.api_rate_windows
                    (client_id, window_start, request_count)
                values (:client_id, :window_start, 1)
                on conflict (client_id, window_start) do update
                set request_count = api_private.api_rate_windows.request_count + 1,
                    updated_at = now()
                where api_private.api_rate_windows.request_count < :request_limit
                returning request_count
                """
            ),
            {
                "client_id": client.id,
                "window_start": window_start,
                "request_limit": client.requests_per_minute,
            },
        )
        count = counter.scalar_one_or_none()
        await self.session.commit()
        if count is None:
            retry_after = max(
                1,
                math.ceil(((window_start + timedelta(minutes=1)) - now).total_seconds()),
            )
            return client, retry_after, 0
        return client, 0, client.requests_per_minute - count

    async def record_usage(
        self,
        *,
        client_id: str,
        request_id: str,
        question_hash: str,
        status_code: int,
        row_count: int,
        duration_ms: float,
    ) -> None:
        await self.session.execute(
            text(
                """
                insert into api_private.api_usage
                    (client_id, request_id, question_hash, status_code, row_count, duration_ms)
                values
                    (
                        :client_id, :request_id, :question_hash,
                        :status_code, :row_count, :duration_ms
                    )
                on conflict (request_id) do nothing
                """
            ),
            {
                "client_id": client_id,
                "request_id": request_id,
                "question_hash": question_hash,
                "status_code": status_code,
                "row_count": row_count,
                "duration_ms": round(duration_ms, 2),
            },
        )
        await self.session.commit()


def hash_question(question: str) -> str:
    return hashlib.sha256(question.encode("utf-8")).hexdigest()
