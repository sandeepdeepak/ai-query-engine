from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.api.routes.sql import get_configured_sql_generator
from app.integrations.ipl_api import get_ipl_client
from app.llm.models import SqlGeneration
from app.main import app
from app.security.api_keys import ApiClient, ApiKeyRegistry
from app.security.dependencies import (
    get_api_access_store,
    get_api_key_registry,
    get_rate_limiter,
)
from app.security.rate_limit import InMemoryRateLimiter


class PublicFakeGenerator:
    provider_name = "test"
    model_name = "test-model"

    async def generate(self, *, system_prompt: str, question: str) -> SqlGeneration:
        return SqlGeneration(
            sql="SELECT match_id FROM matches WHERE season_year = 2026 LIMIT 2",
            explanation="Lists match identifiers.",
            tables_used=["matches"],
            assumptions=[],
            confidence=1,
        )


class PublicFakeIplClient:
    async def execute_plan(self, plan: object) -> list[dict[str, Any]]:
        return [{"match_id": "match-1"}]


def configured_client(tmp_path: Path, *, rpm: int = 10) -> tuple[TestClient, str]:
    registry = ApiKeyRegistry(tmp_path / "clients.json")
    _, api_key = registry.create("Test partner", rpm)
    limiter = InMemoryRateLimiter()
    app.dependency_overrides[get_api_key_registry] = lambda: registry
    app.dependency_overrides[get_rate_limiter] = lambda: limiter
    app.dependency_overrides[get_configured_sql_generator] = lambda: PublicFakeGenerator()
    app.dependency_overrides[get_ipl_client] = lambda: PublicFakeIplClient()
    return TestClient(app), api_key


def test_public_query_requires_api_key(tmp_path: Path) -> None:
    client, _ = configured_client(tmp_path)
    try:
        response = client.post(
            "/public/v1/query", json={"question": "Show two matches"}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"
    assert response.headers["x-request-id"].startswith("req_")


def test_public_query_returns_request_and_rate_metadata(tmp_path: Path) -> None:
    client, api_key = configured_client(tmp_path)
    try:
        response = client.post(
            "/public/v1/query",
            headers={"X-API-Key": api_key},
            json={"question": "Show two matches"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["request_id"].startswith("req_")
    assert response.json()["data"]["row_count"] == 1
    assert response.headers["x-ratelimit-limit"] == "10"
    assert response.headers["x-ratelimit-remaining"] == "9"


def test_public_query_enforces_per_client_rate_limit(tmp_path: Path) -> None:
    client, api_key = configured_client(tmp_path, rpm=1)
    try:
        first = client.post(
            "/public/v1/query",
            headers={"X-API-Key": api_key},
            json={"question": "Show two matches"},
        )
        second = client.post(
            "/public/v1/query",
            headers={"X-API-Key": api_key},
            json={"question": "Show two matches"},
        )
    finally:
        app.dependency_overrides.clear()

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limit_exceeded"
    assert int(second.headers["retry-after"]) > 0


def test_registry_never_persists_plaintext_key(tmp_path: Path) -> None:
    path = tmp_path / "clients.json"
    registry = ApiKeyRegistry(path)
    client, api_key = registry.create("Partner")

    assert api_key not in path.read_text(encoding="utf-8")
    assert registry.authenticate(api_key) == client
    assert registry.authenticate("wrong-key") is None


class RecordingAccessStore:
    recorded: dict[str, object] | None = None

    async def authorize(self, api_key: str):
        return (
            ApiClient(
                id="client_recording",
                name="Recording partner",
                key_prefix="aqe_live_recording",
                key_hash="a" * 64,
                requests_per_minute=10,
                created_at=datetime.now(UTC),
            ),
            0,
            9,
        )

    async def record_usage(self, **values: object) -> None:
        self.recorded = values


def test_public_query_records_privacy_preserving_usage() -> None:
    store = RecordingAccessStore()
    app.dependency_overrides[get_api_access_store] = lambda: store
    app.dependency_overrides[get_configured_sql_generator] = lambda: PublicFakeGenerator()
    app.dependency_overrides[get_ipl_client] = lambda: PublicFakeIplClient()
    try:
        response = TestClient(app).post(
            "/public/v1/query",
            headers={"X-API-Key": "aqe_live_recording"},
            json={"question": "Show two matches"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert store.recorded is not None
    assert store.recorded["client_id"] == "client_recording"
    assert len(str(store.recorded["question_hash"])) == 64
    assert "Show two matches" not in str(store.recorded)
