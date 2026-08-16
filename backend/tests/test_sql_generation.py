from fastapi.testclient import TestClient

from app.api.routes.sql import get_configured_sql_generator
from app.llm.models import SqlGeneration
from app.llm.schema_selector import SchemaSelector
from app.main import app
from app.schema.service import SchemaService


class FakeSqlGenerator:
    provider_name = "test"
    model_name = "test-model"
    received_prompt = ""

    async def generate(self, *, system_prompt: str, question: str) -> SqlGeneration:
        self.received_prompt = system_prompt
        assert question == (
            "Using IPL cricket data, answer this request: Show matches from the 2026 season"
        )
        return SqlGeneration(
            sql="SELECT match_id FROM matches WHERE season_year = 2026 LIMIT 100",
            explanation="Lists 2026 match identifiers.",
            tables_used=["matches"],
            assumptions=[],
            confidence=0.95,
        )


def test_generate_sql_returns_structured_stages() -> None:
    generator = FakeSqlGenerator()
    app.dependency_overrides[get_configured_sql_generator] = lambda: generator
    try:
        response = TestClient(app).post(
            "/api/v1/sql/generate",
            json={"question": "Show matches from the 2026 season"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "test"
    assert payload["selected_tables"]
    assert payload["generation"]["sql"].startswith("SELECT")
    assert [stage["name"] for stage in payload["stages"]] == [
        "question_clarification",
        "schema_selection",
        "prompt_building",
        "sql_generation",
    ]
    assert "TABLE matches" in generator.received_prompt
    assert "Royal Challengers Bangaluru" in generator.received_prompt
    assert "Royal Challengers Bengaluru" in generator.received_prompt
    assert payload["clarification"]["interpreted_question"].startswith("Using IPL")


def test_top_run_scorers_are_clarified_as_player_batting_totals() -> None:
    from app.integrations.ipl_api import IplApiClient
    from app.llm.question_clarifier import IplQuestionClarifier

    clarification = IplQuestionClarifier().clarify(
        "Show top run scorers of Royal Challengers Bengaluru from the 2026 season"
    )

    assert "individual batting runs" in clarification.interpreted_question
    assert "while batting for Royal Challengers Bengaluru" in clarification.interpreted_question
    assert "not team innings totals" in clarification.interpreted_question

    selected = SchemaSelector().select(
        clarification.interpreted_question, SchemaService().get_catalog()
    )
    assert selected[0].name == "batting_stats"
    assert "batting_stats" in IplApiClient.ALLOWED_RESOURCES


def test_generate_sql_rejects_short_question() -> None:
    response = TestClient(app).post("/api/v1/sql/generate", json={"question": "x"})
    assert response.status_code == 422


def test_schema_selection_excludes_weak_column_only_matches() -> None:
    catalog = SchemaService().get_catalog()
    selected = SchemaSelector().select("Show matches from the 2026 season", catalog)

    assert [table.name for table in selected] == ["matches", "seasons"]


class InvalidTableGenerator(FakeSqlGenerator):
    async def generate(self, *, system_prompt: str, question: str) -> SqlGeneration:
        return SqlGeneration(
            sql="SELECT * FROM secret_table",
            explanation="Invalid test output.",
            tables_used=["secret_table"],
            assumptions=[],
            confidence=0.1,
        )


def test_generate_sql_rejects_table_outside_context() -> None:
    app.dependency_overrides[get_configured_sql_generator] = lambda: InvalidTableGenerator()
    try:
        response = TestClient(app).post(
            "/api/v1/sql/generate",
            json={"question": "Show matches from the 2026 season"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"] == "Generator referenced a table outside the selected schema"
