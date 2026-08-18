import pytest

from app.query.validator import SqlValidationError, SqlValidator
from app.schema.service import SchemaService


@pytest.fixture
def validator_and_catalog():
    return SqlValidator(), SchemaService().get_catalog()


def test_valid_select_builds_bounded_rest_plan(validator_and_catalog) -> None:
    validator, catalog = validator_and_catalog
    result = validator.validate(
        "SELECT match_id, match_date FROM matches "
        "WHERE season_year = 2026 AND status = 'completed' "
        "ORDER BY match_date DESC LIMIT 500",
        catalog,
        max_rows=100,
    )

    assert result.valid is True
    assert result.limit_applied is True
    assert result.plan.table == "matches"
    assert result.plan.select == "match_id,match_date"
    assert result.plan.limit == 100
    assert result.plan.order == "match_date.desc"
    assert result.plan.or_filters == []
    assert [(item.column, item.operator, item.value) for item in result.plan.filters] == [
        ("season_year", "eq", "2026"),
        ("status", "eq", "completed"),
    ]


@pytest.mark.parametrize(
    ("sql", "message"),
    [
        ("DELETE FROM matches", "Exactly one SELECT"),
        ("SELECT * FROM matches; SELECT * FROM players", "Exactly one SELECT"),
        ("SELECT secret FROM matches", "Unknown columns"),
        ("SELECT COUNT(*) FROM matches", "Aggregate functions"),
        ("SELECT * FROM matches JOIN innings USING (match_id)", "Joins are not supported"),
        ("SELECT pg_sleep(10) FROM matches", "SQL functions"),
    ],
)
def test_unsafe_or_unsupported_sql_is_rejected(
    validator_and_catalog, sql: str, message: str
) -> None:
    validator, catalog = validator_and_catalog
    with pytest.raises(SqlValidationError, match=message):
        validator.validate(sql, catalog)


def test_validate_endpoint_returns_safe_plan() -> None:
    from fastapi.testclient import TestClient

    from app.main import app

    response = TestClient(app).post(
        "/api/v1/sql/validate",
        json={"sql": "SELECT player_id, player_name FROM players ORDER BY player_name"},
    )

    assert response.status_code == 200
    assert response.json()["plan"]["limit"] == 100


def test_team_participation_builds_home_or_away_filter(validator_and_catalog) -> None:
    validator, catalog = validator_and_catalog
    result = validator.validate(
        "SELECT match_id, match_date, home_team_name, away_team_name FROM matches "
        "WHERE season_year = 2026 AND "
        "(home_team_name = 'Royal Challengers Bengaluru' OR "
        "away_team_name = 'Royal Challengers Bengaluru') "
        "ORDER BY match_date DESC LIMIT 2",
        catalog,
    )

    assert [(item.column, item.operator, item.value) for item in result.plan.filters] == [
        ("season_year", "eq", "2026")
    ]
    assert [(item.column, item.operator, item.value) for item in result.plan.or_filters] == [
        ("home_team_name", "eq", "Royal Challengers Bengaluru"),
        ("away_team_name", "eq", "Royal Challengers Bengaluru"),
    ]


def test_or_group_supports_safe_non_equality_comparisons(validator_and_catalog) -> None:
    validator, catalog = validator_and_catalog
    result = validator.validate(
        "SELECT bowler_name, wickets, economy FROM bowling_stats "
        "WHERE season_year = 2026 AND (wickets > 20 OR economy < 7) "
        "ORDER BY wickets DESC LIMIT 10",
        catalog,
    )

    assert [(item.column, item.operator, item.value) for item in result.plan.filters] == [
        ("season_year", "eq", "2026")
    ]
    assert [(item.column, item.operator, item.value) for item in result.plan.or_filters] == [
        ("wickets", "gt", "20"),
        ("economy", "lt", "7"),
    ]
