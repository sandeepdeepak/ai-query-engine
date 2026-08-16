from datetime import UTC, datetime, timedelta
from time import monotonic

from app.schema.catalog import IPL_RELATIONSHIPS, IPL_SCHEMA_CATALOG
from app.schema.models import (
    ColumnMetadata,
    RelationshipMetadata,
    ResourceVerification,
    SchemaCatalog,
    SchemaVerification,
    TableMetadata,
)


class SchemaService:
    def __init__(self, ttl_seconds: int = 900) -> None:
        self._ttl_seconds = ttl_seconds
        self._cached_catalog: SchemaCatalog | None = None
        self._cache_deadline = 0.0

    def get_catalog(self, *, refresh: bool = False) -> SchemaCatalog:
        if refresh or self._cached_catalog is None or monotonic() >= self._cache_deadline:
            now = datetime.now(UTC)
            tables = [
                TableMetadata(
                    name=table["name"],
                    description=table["description"],
                    primary_key=table["primary_key"],
                    columns=[
                        ColumnMetadata(
                            name=name,
                            data_type=data_type,
                            nullable=nullable,
                            description=description,
                        )
                        for name, data_type, nullable, description in table["columns"]
                    ],
                )
                for table in IPL_SCHEMA_CATALOG
            ]
            self._cached_catalog = SchemaCatalog(
                source="ipl-public-api",
                dialect="postgresql",
                generated_at=now,
                expires_at=now + timedelta(seconds=self._ttl_seconds),
                tables=tables,
                relationships=[RelationshipMetadata(**item) for item in IPL_RELATIONSHIPS],
            )
            self._cache_deadline = monotonic() + self._ttl_seconds
        return self._cached_catalog.model_copy(deep=True)

    def get_table(self, table_name: str) -> TableMetadata | None:
        return next(
            (table for table in self.get_catalog().tables if table.name == table_name),
            None,
        )

    async def verify(self, client: object) -> SchemaVerification:
        resources: list[ResourceVerification] = []
        for table in self.get_catalog().tables:
            columns = [column.name for column in table.columns]
            try:
                accessible = await client.probe_resource(table.name, columns)
                if not accessible:
                    raise ValueError("Resource probe failed")
                resources.append(ResourceVerification(table=table.name, accessible=True))
            except Exception:
                resources.append(
                    ResourceVerification(
                        table=table.name,
                        accessible=False,
                        error="Resource or catalog columns are unavailable",
                    )
                )
        status = "ready" if all(item.accessible for item in resources) else "degraded"
        return SchemaVerification(status=status, resources=resources)
