from typing import Any, Literal

from pydantic import BaseModel, Field

from app.llm.models import GenerateSqlResponse, GenerationStage


class ValidateSqlRequest(BaseModel):
    sql: str = Field(min_length=1, max_length=20_000)
    max_rows: int = Field(default=100, ge=1, le=100)


class RestFilter(BaseModel):
    column: str
    operator: Literal["eq", "neq", "gt", "gte", "lt", "lte", "is", "in"]
    value: str


class QueryPlan(BaseModel):
    table: str
    select: str
    filters: list[RestFilter]
    or_filters: list[RestFilter] = Field(default_factory=list)
    order: str | None
    limit: int


class ValidationResult(BaseModel):
    valid: Literal[True]
    query_type: Literal["SELECT"]
    normalized_sql: str
    tables: list[str]
    columns: list[str]
    limit_applied: bool
    plan: QueryPlan


class QueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    max_rows: int = Field(default=100, ge=1, le=100)


class ResultColumn(BaseModel):
    name: str
    data_type: str


class QueryData(BaseModel):
    columns: list[ResultColumn]
    rows: list[dict[str, Any]]
    row_count: int


class ExecutionMetadata(BaseModel):
    execution_time_ms: float
    truncated: bool


class QueryResponse(BaseModel):
    request_id: str | None = None
    question: str
    status: Literal["completed"]
    stages: list[GenerationStage]
    generation: GenerateSqlResponse
    validation: ValidationResult
    data: QueryData
    metadata: ExecutionMetadata
