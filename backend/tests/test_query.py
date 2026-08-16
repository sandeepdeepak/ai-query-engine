from typing import Any

from fastapi.testclient import TestClient

from app.api.routes.sql import get_configured_sql_generator
from app.integrations.ipl_api import get_ipl_client
from app.llm.models import SqlGeneration
from app.main import app


class FakeSqlGenerator:
    provider_name = "test"
    model_name = "test-model"

    async def generate(self, *, system_prompt: str, question: str) -> SqlGeneration:
        assert "Do not use aggregate" in system_prompt
        return SqlGeneration(
            sql=(
                "SELECT match_id, match_date, home_team_name, away_team_name "
                "FROM matches WHERE season_year = 2026 ORDER BY match_date LIMIT 10"
            ),
            explanation="Lists 2026 matches.",
            tables_used=["matches"],
            assumptions=[],
            confidence=0.98,
        )


class FakeIplClient:
    received_plan: Any = None

    async def execute_plan(self, plan: object) -> list[dict[str, Any]]:
        self.received_plan = plan
        return [
            {
                "match_id": "2026-01",
                "match_date": "2026-03-22",
                "home_team_name": "Team A",
                "away_team_name": "Team B",
            }
        ]


def test_query_endpoint_runs_generation_validation_and_execution() -> None:
    client = FakeIplClient()
    app.dependency_overrides[get_configured_sql_generator] = lambda: FakeSqlGenerator()
    app.dependency_overrides[get_ipl_client] = lambda: client
    try:
        response = TestClient(app).post(
            "/api/v1/query",
            json={"question": "Show matches from the 2026 season", "max_rows": 25},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["validation"]["valid"] is True
    assert payload["data"]["row_count"] == 1
    assert payload["data"]["rows"][0]["match_id"] == "2026-01"
    assert [stage["name"] for stage in payload["stages"]][-3:] == [
        "sql_validation",
        "execution",
        "result_formatting",
    ]
    assert client.received_plan.limit == 10


def test_development_cors_accepts_both_loopback_frontend_origins() -> None:
    client = TestClient(app)
    for origin in ("http://localhost:5173", "http://127.0.0.1:5173"):
        response = client.options(
            "/api/v1/query",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
