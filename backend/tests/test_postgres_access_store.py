from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.security.access_store import PostgresApiAccessStore, hash_question


def client_result() -> MagicMock:
    result = MagicMock()
    result.mappings.return_value.one_or_none.return_value = {
        "id": "client_test",
        "name": "Partner",
        "key_prefix": "aqe_live_example",
        "key_hash": "a" * 64,
        "active": True,
        "requests_per_minute": 10,
        "created_at": datetime.now(UTC),
    }
    return result


@pytest.mark.asyncio
async def test_postgres_store_atomically_consumes_rate_window() -> None:
    counter = MagicMock()
    counter.scalar_one_or_none.return_value = 1
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[client_result(), counter])
    session.commit = AsyncMock()

    client, retry_after, remaining = await PostgresApiAccessStore(session).authorize(
        "aqe_live_example"
    )

    assert client is not None
    assert client.id == "client_test"
    assert retry_after == 0
    assert remaining == 9
    assert "on conflict (client_id, window_start) do update" in str(
        session.execute.await_args_list[1].args[0]
    )
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_postgres_store_rejects_full_rate_window() -> None:
    counter = MagicMock()
    counter.scalar_one_or_none.return_value = None
    session = MagicMock()
    session.execute = AsyncMock(side_effect=[client_result(), counter])
    session.commit = AsyncMock()

    client, retry_after, remaining = await PostgresApiAccessStore(session).authorize(
        "aqe_live_example"
    )

    assert client is not None
    assert retry_after > 0
    assert remaining == 0


def test_question_audit_uses_digest_not_plaintext() -> None:
    question = "Show the last two RCB matches"
    digest = hash_question(question)

    assert len(digest) == 64
    assert question not in digest


def test_supabase_schema_is_private_and_indexed() -> None:
    sql = (
        Path(__file__).parents[2] / "infra" / "supabase" / "api_access.sql"
    ).read_text(encoding="utf-8")

    assert "create schema if not exists api_private" in sql
    assert "revoke all on schema api_private from public, anon, authenticated" in sql
    assert "enable row level security" in sql
    assert "create role api_query_engine nologin" in sql
    assert "to api_query_engine" in sql
    assert "api_usage_client_created_idx" in sql
    assert "primary key (client_id, window_start)" in sql
