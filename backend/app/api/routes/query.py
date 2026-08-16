from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from openai import APIError

from app.api.routes.sql import get_configured_sql_generator
from app.integrations.ipl_api import IplApiClient, get_ipl_client
from app.llm.provider import SqlGenerator
from app.llm.service import SqlGenerationService
from app.query.models import QueryRequest, QueryResponse
from app.query.service import QueryService
from app.query.validator import SqlValidationError, SqlValidator
from app.schema.dependencies import get_schema_service
from app.schema.service import SchemaService

router = APIRouter(prefix="/query")


@router.post("", response_model=QueryResponse)
async def run_query(
    request: QueryRequest,
    schema_service: Annotated[SchemaService, Depends(get_schema_service)],
    generator: Annotated[SqlGenerator, Depends(get_configured_sql_generator)],
    client: Annotated[IplApiClient, Depends(get_ipl_client)],
) -> QueryResponse:
    return await execute_query(request, schema_service, generator, client)


async def execute_query(
    request: QueryRequest,
    schema_service: SchemaService,
    generator: SqlGenerator,
    client: IplApiClient,
) -> QueryResponse:
    generation_service = SqlGenerationService(
        schema_service=schema_service,
        generator=generator,
    )
    service = QueryService(
        generation_service=generation_service,
        schema_service=schema_service,
        validator=SqlValidator(),
        client=client,
    )
    try:
        return await service.run(request)
    except SqlValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Generated SQL cannot be safely executed: {exc}",
        ) from exc
    except APIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI provider request failed",
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="IPL data source request failed",
        ) from exc
