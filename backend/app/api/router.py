from fastapi import APIRouter

from app.api.routes import health, query, schema, sql

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(schema.router, tags=["schema"])
api_router.include_router(sql.router, tags=["sql-generation"])
api_router.include_router(query.router, tags=["query"])
