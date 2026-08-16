from time import perf_counter

from app.integrations.ipl_api import IplApiClient
from app.llm.models import GenerationStage
from app.llm.service import SqlGenerationService
from app.query.models import (
    ExecutionMetadata,
    QueryData,
    QueryRequest,
    QueryResponse,
    ResultColumn,
)
from app.query.validator import SqlValidator
from app.schema.service import SchemaService


class QueryService:
    def __init__(
        self,
        *,
        generation_service: SqlGenerationService,
        schema_service: SchemaService,
        validator: SqlValidator,
        client: IplApiClient,
    ) -> None:
        self._generation_service = generation_service
        self._schema_service = schema_service
        self._validator = validator
        self._client = client

    async def run(self, request: QueryRequest) -> QueryResponse:
        generation = await self._generation_service.generate(request.question)
        catalog = self._schema_service.get_catalog()
        validation = self._validator.validate(
            generation.generation.sql,
            catalog,
            max_rows=request.max_rows,
        )
        started = perf_counter()
        rows = await self._client.execute_plan(validation.plan)
        elapsed_ms = (perf_counter() - started) * 1000
        table = next(item for item in catalog.tables if item.name == validation.plan.table)
        types = {column.name: column.data_type for column in table.columns}
        column_names = (
            list(rows[0].keys()) if rows else self._selected_names(validation.plan.select)
        )
        data = QueryData(
            columns=[
                ResultColumn(name=name, data_type=types.get(name, "unknown"))
                for name in column_names
            ],
            rows=rows,
            row_count=len(rows),
        )
        return QueryResponse(
            question=request.question,
            status="completed",
            stages=[
                *generation.stages,
                GenerationStage(name="sql_validation", status="success"),
                GenerationStage(name="execution", status="success"),
                GenerationStage(name="result_formatting", status="success"),
            ],
            generation=generation,
            validation=validation,
            data=data,
            metadata=ExecutionMetadata(
                execution_time_ms=round(elapsed_ms, 2),
                truncated=len(rows) == validation.plan.limit,
            ),
        )

    @staticmethod
    def _selected_names(select: str) -> list[str]:
        if select == "*":
            return []
        return [item.split(":", maxsplit=1)[0] for item in select.split(",")]
