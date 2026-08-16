from fastapi.testclient import TestClient

from app.integrations.ipl_api import get_ipl_client
from app.main import app
from app.schema.service import SchemaService


class FakeIplClient:
    async def probe_resource(self, resource: str, columns: list[str]) -> bool:
        assert columns
        return resource != "deliveries"


def test_schema_catalog_contains_verified_resources() -> None:
    response = TestClient(app).get("/api/v1/schema")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "ipl-public-api"
    assert {table["name"] for table in payload["tables"]} == {
        "matches",
        "players",
        "deliveries",
        "innings",
        "seasons",
    }
    matches = next(table for table in payload["tables"] if table["name"] == "matches")
    assert "match_id" in {column["name"] for column in matches["columns"]}


def test_table_schema_and_unknown_table() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/schema/deliveries")
    missing = client.get("/api/v1/schema/not_a_table")

    assert response.status_code == 200
    assert response.json()["primary_key"] == ["match_id", "innings_number", "sequence"]
    assert missing.status_code == 404


def test_schema_service_returns_defensive_cached_copy() -> None:
    service = SchemaService(ttl_seconds=60)
    first = service.get_catalog()
    first.tables.clear()
    second = service.get_catalog()

    assert len(second.tables) == 5
    assert first.generated_at == second.generated_at


def test_verification_reports_degraded_resource() -> None:
    app.dependency_overrides[get_ipl_client] = lambda: FakeIplClient()
    try:
        response = TestClient(app).get("/api/v1/schema/verify")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    failed = [item for item in response.json()["resources"] if not item["accessible"]]
    assert failed == [
        {
            "table": "deliveries",
            "accessible": False,
            "error": "Resource or catalog columns are unavailable",
        }
    ]
