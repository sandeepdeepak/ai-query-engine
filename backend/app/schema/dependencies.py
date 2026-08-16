from functools import lru_cache

from app.core.config import get_settings
from app.schema.service import SchemaService


@lru_cache
def get_schema_service() -> SchemaService:
    return SchemaService(ttl_seconds=get_settings().schema_cache_ttl_seconds)
