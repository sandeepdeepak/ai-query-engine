import secrets
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.security.api_keys import ApiClient, ApiKeyRegistry


class PostgresApiKeyAdmin:
    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine

    async def create(
        self, name: str, requests_per_minute: int = 10
    ) -> tuple[ApiClient, str]:
        api_key = ApiKeyRegistry.generate_key()
        client = ApiClient(
            id=f"client_{secrets.token_hex(8)}",
            name=name,
            key_prefix=api_key[:18],
            key_hash=ApiKeyRegistry.hash_key(api_key),
            requests_per_minute=requests_per_minute,
            created_at=datetime.now(UTC),
        )
        async with self.engine.begin() as connection:
            await connection.execute(
                text(
                    """
                    insert into api_private.api_clients
                        (id, name, key_prefix, key_hash, active, requests_per_minute, created_at)
                    values
                        (:id, :name, :key_prefix, :key_hash, true, :rpm, :created_at)
                    """
                ),
                {
                    "id": client.id,
                    "name": client.name,
                    "key_prefix": client.key_prefix,
                    "key_hash": client.key_hash,
                    "rpm": client.requests_per_minute,
                    "created_at": client.created_at,
                },
            )
        return client, api_key

    async def list(self) -> list[ApiClient]:
        async with self.engine.connect() as connection:
            result = await connection.execute(
                text(
                    """
                    select id, name, key_prefix, key_hash, active, requests_per_minute, created_at
                    from api_private.api_clients
                    order by created_at
                    """
                )
            )
        return [ApiClient.model_validate(dict(row)) for row in result.mappings()]

    async def revoke(self, client_id: str) -> bool:
        async with self.engine.begin() as connection:
            result = await connection.execute(
                text(
                    """
                    update api_private.api_clients
                    set active = false, revoked_at = now()
                    where id = :client_id and active = true
                    """
                ),
                {"client_id": client_id},
            )
        return bool(result.rowcount)
