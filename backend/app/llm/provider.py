from typing import Protocol

from openai import AsyncOpenAI

from app.llm.models import QuestionClarification, SqlGeneration

INTENT_ANALYSIS_PROMPT = """Analyze every user question as an IPL cricket data intent.
Return a clear standalone interpreted question before SQL generation, plus structured intent.

IPL semantic defaults:
- "highest run" or "highest runs" without season/career/total wording means the highest
  individual batter score in one match innings across the requested scope. Use match-level
  batting intent, order runs descending, and return one result.
- "most runs", "top run scorer", "leading run scorer", and Orange Cap mean accumulated
  batter runs for a season/team/career scope, never runs on one delivery.
- Purple Cap means the season bowler with the most bowler-credited wickets.
- A raw delivery run value is intended only when the user explicitly says ball or delivery.
- Preserve every explicit season, team, player, venue, opponent, and result-count filter.
- Normalize grammar and spelling without changing the user's requested scope.
- If scope is omitted, state the IPL-wide default explicitly.
- result_limit is 1 for singular superlatives such as highest, best, winner, or most.

Use concise values for entity, metric, scope, and ranking. Do not generate SQL.
"""


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

    async def clarify(
        self, *, question: str, domain_hint: str
    ) -> QuestionClarification:
        response = await self._client.responses.parse(
            model=self.model_name,
            input=[
                {"role": "system", "content": INTENT_ANALYSIS_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Original question: {question}\n"
                        f"Deterministic IPL guardrail: {domain_hint}"
                    ),
                },
            ],
            text_format=QuestionClarification,
        )
        if response.output_parsed is None:
            raise RuntimeError("The model did not return an IPL intent analysis")
        return response.output_parsed.model_copy(update={"original_question": question})


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
