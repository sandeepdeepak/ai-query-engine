from typing import Protocol

from openai import AsyncOpenAI

from app.llm.models import SqlGeneration


class SqlGenerator(Protocol):
    provider_name: str
    model_name: str

    async def generate(self, *, system_prompt: str, question: str) -> SqlGeneration: ...


class OpenAiSqlGenerator:
    provider_name = "openai"

    def __init__(self, *, api_key: str, model: str) -> None:
        self.model_name = model
        self._client = AsyncOpenAI(api_key=api_key)

    async def generate(self, *, system_prompt: str, question: str) -> SqlGeneration:
        response = await self._client.responses.parse(
            model=self.model_name,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
            text_format=SqlGeneration,
        )
        if response.output_parsed is None:
            raise RuntimeError("The model did not return a SQL generation result")
        return response.output_parsed


class MockSqlGenerator:
    provider_name = "mock"
    model_name = "deterministic-development-generator"

    async def generate(self, *, system_prompt: str, question: str) -> SqlGeneration:
        lowered = question.lower()
        if "season" in lowered and "2026" in lowered:
            sql = (
                "SELECT match_id, match_date, home_team_name, away_team_name, "
                "venue, result_text FROM matches WHERE season_year = 2026 "
                "ORDER BY match_date LIMIT 100"
            )
            explanation = "Lists 2026 IPL matches in date order."
            tables = ["matches"]
        elif "player" in lowered:
            sql = (
                "SELECT player_id, player_name, first_seen_season, last_seen_season "
                "FROM players ORDER BY player_name LIMIT 100"
            )
            explanation = "Lists players and their IPL season range."
            tables = ["players"]
        else:
            sql = "SELECT * FROM matches ORDER BY match_date DESC LIMIT 100"
            explanation = "Returns the latest IPL matches."
            tables = ["matches"]
        return SqlGeneration(
            sql=sql,
            explanation=explanation,
            tables_used=tables,
            assumptions=[
                "The deterministic local generator is enabled; configure OpenAI for AI output."
            ],
            confidence=0.5,
        )
