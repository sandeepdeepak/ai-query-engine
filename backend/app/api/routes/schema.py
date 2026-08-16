from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.integrations.ipl_api import IplApiClient, get_ipl_client
from app.schema.dependencies import get_schema_service
from app.schema.models import SchemaCatalog, SchemaVerification, TableMetadata
from app.schema.service import SchemaService

router = APIRouter(prefix="/schema")


@router.get("", response_model=SchemaCatalog)
async def get_schema(
    service: Annotated[SchemaService, Depends(get_schema_service)],
    refresh: Annotated[bool, Query(description="Rebuild the in-process metadata cache")] = False,
) -> SchemaCatalog:
    return service.get_catalog(refresh=refresh)


@router.get("/verify", response_model=SchemaVerification)
async def verify_schema(
    service: Annotated[SchemaService, Depends(get_schema_service)],
    client: Annotated[IplApiClient, Depends(get_ipl_client)],
) -> SchemaVerification:
    return await service.verify(client)


@router.get("/{table_name}", response_model=TableMetadata)
async def get_table_schema(
    table_name: str,
    service: Annotated[SchemaService, Depends(get_schema_service)],
) -> TableMetadata:
    table = service.get_table(table_name)
    if table is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unknown IPL API table",
        )
    return table
