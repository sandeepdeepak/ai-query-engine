from fastapi.testclient import TestClient

from app.integrations.ipl_api import get_ipl_client
from app.main import app


class FakeIplClient:
    async def get_matches(self, season_year: int, limit: int = 10) -> list[dict[str, object]]:
        assert season_year == 2026
        assert limit == 1
        return [{"match_id": "example"}]


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "ai-query-engine-api",
    }


def test_openapi_is_available() -> None:
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "AI Query Engine"


def test_ipl_data_source_health() -> None:
    app.dependency_overrides[get_ipl_client] = lambda: FakeIplClient()
    try:
        with TestClient(app) as client:
            response = client.get("/api/v1/health/data-source")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "source": "ipl-public-api",
        "sample_records": 1,
    }
