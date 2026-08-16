from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from openai import APIError

from app.llm.dependencies import AiProviderConfigurationError, get_sql_generator
from app.llm.models import GenerateSqlRequest, GenerateSqlResponse
from app.llm.provider import SqlGenerator
from app.llm.service import SqlGenerationService
from app.query.models import ValidateSqlRequest, ValidationResult
from app.query.validator import SqlValidationError, SqlValidator
from app.schema.dependencies import get_schema_service
from app.schema.service import SchemaService

router = APIRouter(prefix="/sql")


def get_configured_sql_generator() -> SqlGenerator:
    try:
        return get_sql_generator()
    except AiProviderConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/validate", response_model=ValidationResult)
async def validate_sql(
    request: ValidateSqlRequest,
    schema_service: Annotated[SchemaService, Depends(get_schema_service)],
) -> ValidationResult:
    try:
        return SqlValidator().validate(
            request.sql,
            schema_service.get_catalog(),
            max_rows=request.max_rows,
        )
    except SqlValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.post("/generate", response_model=GenerateSqlResponse)
async def generate_sql(
    request: GenerateSqlRequest,
    schema_service: Annotated[SchemaService, Depends(get_schema_service)],
    generator: Annotated[SqlGenerator, Depends(get_configured_sql_generator)],
) -> GenerateSqlResponse:
    service = SqlGenerationService(schema_service=schema_service, generator=generator)
    try:
        return await service.generate(request.question)
    except APIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider request failed",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
