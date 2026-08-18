from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from app.api.routes.query import execute_query
from app.api.routes.sql import get_configured_sql_generator
from app.integrations.ipl_api import IplApiClient, get_ipl_client
from app.llm.provider import SqlGenerator
from app.query.models import QueryRequest, QueryResponse
from app.schema.dependencies import get_schema_service
from app.schema.models import SchemaCatalog
from app.schema.service import SchemaService
from app.security.access_store import hash_question
from app.security.api_keys import ApiClient
from app.security.dependencies import enforce_rate_limit

router = APIRouter()


def add_client_headers(response: Response, request: Request, client: ApiClient) -> None:
    response.headers["X-RateLimit-Limit"] = str(request.state.rate_limit)
    response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)
    response.headers["X-API-Client"] = client.id


@router.get(
    "/schema",
    response_model=SchemaCatalog,
    summary="Get the queryable IPL schema",
    description=(
        "Returns every queryable table and analytics view with primary keys, column types, "
        "column descriptions, and verified relationships. Supply X-API-Key."
    ),
    responses={
        401: {"description": "Missing, invalid, or revoked API key"},
        429: {"description": "Per-client rate limit exceeded"},
    },
)
async def public_schema(
    request: Request,
    response: Response,
    api_client: Annotated[ApiClient, Depends(enforce_rate_limit)],
    schema_service: Annotated[SchemaService, Depends(get_schema_service)],
) -> SchemaCatalog:
    add_client_headers(response, request, api_client)
    return schema_service.get_catalog()


@router.post(
    "/query",
    response_model=QueryResponse,
    summary="Run a natural-language IPL query",
    description=(
        "Generates validated read-only SQL and returns IPL data. "
        "Supply the client credential in the X-API-Key header."
    ),
    responses={
        401: {"description": "Missing, invalid, or revoked API key"},
        429: {"description": "Per-client rate limit exceeded"},
        502: {"description": "AI provider or IPL data source failure"},
    },
)
async def public_query(
    payload: QueryRequest,
    request: Request,
    response: Response,
    api_client: Annotated[ApiClient, Depends(enforce_rate_limit)],
    schema_service: Annotated[SchemaService, Depends(get_schema_service)],
    generator: Annotated[SqlGenerator, Depends(get_configured_sql_generator)],
    ipl_client: Annotated[IplApiClient, Depends(get_ipl_client)],
) -> QueryResponse:
    started = perf_counter()
    result = await execute_query(payload, schema_service, generator, ipl_client)
    await request.state.api_access_store.record_usage(
        client_id=api_client.id,
        request_id=request.state.request_id,
        question_hash=hash_question(payload.question),
        status_code=200,
        row_count=result.data.row_count,
        duration_ms=(perf_counter() - started) * 1000,
    )
    add_client_headers(response, request, api_client)
    return result.model_copy(update={"request_id": request.state.request_id})
