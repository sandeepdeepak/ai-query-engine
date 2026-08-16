from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ColumnMetadata(BaseModel):
    name: str
    data_type: Literal["text", "integer", "numeric", "boolean", "date", "time", "timestamp"]
    nullable: bool
    description: str


class TableMetadata(BaseModel):
    name: str
    description: str
    primary_key: list[str]
    columns: list[ColumnMetadata]


class RelationshipMetadata(BaseModel):
    from_table: str
    from_column: str
    to_table: str
    to_column: str


class SchemaCatalog(BaseModel):
    source: Literal["ipl-public-api"]
    dialect: Literal["postgresql"]
    generated_at: datetime
    expires_at: datetime
    tables: list[TableMetadata]
    relationships: list[RelationshipMetadata]


class ResourceVerification(BaseModel):
    table: str
    accessible: bool
    error: str | None = None


class SchemaVerification(BaseModel):
    status: Literal["ready", "degraded"]
    resources: list[ResourceVerification]
