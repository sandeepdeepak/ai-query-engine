from typing import Literal

from pydantic import BaseModel, Field, field_validator


class SqlGeneration(BaseModel):
    sql: str = Field(description="A single read-only PostgreSQL SELECT statement")
    explanation: str
    tables_used: list[str]
    assumptions: list[str]
    confidence: float = Field(ge=0, le=1)

    @field_validator("sql")
    @classmethod
    def normalize_sql(cls, value: str) -> str:
        sql = value.strip()
        if sql.startswith("```"):
            raise ValueError("SQL must not contain Markdown fences")
        return sql.rstrip(";")


class QuestionClarification(BaseModel):
    original_question: str
    interpreted_question: str
    assumptions: list[str] = Field(default_factory=list)


class GenerationStage(BaseModel):
    name: Literal[
        "question_clarification",
        "schema_selection",
        "prompt_building",
        "sql_generation",
        "sql_validation",
        "execution",
        "result_formatting",
    ]
    status: Literal["success"]


class GenerateSqlRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)

    @field_validator("question")
    @classmethod
    def clean_question(cls, value: str) -> str:
        return " ".join(value.split())


class GenerateSqlResponse(BaseModel):
    question: str
    clarification: QuestionClarification
    provider: str
    model: str
    selected_tables: list[str]
    stages: list[GenerationStage]
    generation: SqlGeneration
