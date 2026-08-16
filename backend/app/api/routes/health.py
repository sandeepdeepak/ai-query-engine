from typing import Annotated, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from app.db.session import engine
from app.integrations.ipl_api import IplApiClient, IplApiConfigurationError, get_ipl_client

router = APIRouter(prefix="/health")


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str


class ReadinessResponse(BaseModel):
    status: Literal["ready"]
    database: Literal["connected"]


class DataSourceResponse(BaseModel):
    status: Literal["ready"]
    source: Literal["ipl-public-api"]
    sample_records: int


@router.get("", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="ai-query-engine-api")


@router.get("/ready", response_model=ReadinessResponse)
async def readiness() -> ReadinessResponse:
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable",
        ) from exc

    return ReadinessResponse(status="ready", database="connected")


@router.get("/data-source", response_model=DataSourceResponse)
async def data_source_readiness(
    client: Annotated[IplApiClient, Depends(get_ipl_client)],
) -> DataSourceResponse:
    try:
        matches = await client.get_matches(season_year=2026, limit=1)
    except IplApiConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="IPL data source is unavailable",
        ) from exc

    return DataSourceResponse(
        status="ready",
        source="ipl-public-api",
        sample_records=len(matches),
    )
