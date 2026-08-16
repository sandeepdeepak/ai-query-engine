from typing import Any

import httpx

from app.core.config import get_settings


class IplApiConfigurationError(RuntimeError):
    pass


class IplApiClient:
    ALLOWED_RESOURCES = frozenset(
        {"matches", "players", "batting_stats", "deliveries", "innings", "seasons"}
    )

    def __init__(self, base_url: str, api_key: str, timeout_seconds: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout_seconds

    async def get_matches(self, season_year: int, limit: int = 10) -> list[dict[str, Any]]:
        return await self.get_records(
            "matches",
            filters={"season_year": f"eq.{season_year}"},
            limit=limit,
        )

    async def get_records(
        self,
        resource: str,
        *,
        filters: dict[str, str] | None = None,
        select: str = "*",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        if resource not in self.ALLOWED_RESOURCES:
            raise ValueError(f"Unsupported IPL API resource: {resource}")

        safe_limit = min(max(limit, 1), 100)
        params: dict[str, str | int] = {"select": select, "limit": safe_limit}
        if filters:
            params.update(filters)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._base_url}/{resource}",
                params=params,
                headers={"apikey": self._api_key},
            )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("IPL API returned an unexpected response shape")
        return payload

    async def execute_plan(self, plan: object) -> list[dict[str, Any]]:
        resource = plan.table
        if resource not in self.ALLOWED_RESOURCES:
            raise ValueError(f"Unsupported IPL API resource: {resource}")
        params: list[tuple[str, str | int]] = [
            ("select", plan.select),
            ("limit", plan.limit),
        ]
        params.extend(
            (item.column, f"{item.operator}.{item.value}") for item in plan.filters
        )
        if plan.or_filters:
            alternatives = ",".join(
                f"{item.column}.{item.operator}.{item.value}" for item in plan.or_filters
            )
            params.append(("or", f"({alternatives})"))
        if plan.order:
            params.append(("order", plan.order))
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(
                f"{self._base_url}/{resource}",
                params=params,
                headers={"apikey": self._api_key},
            )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("IPL API returned an unexpected response shape")
        return payload

    async def probe_resource(self, resource: str, columns: list[str]) -> bool:
        await self.get_records(resource, select=",".join(columns), limit=1)
        return True


def get_ipl_client() -> IplApiClient:
    settings = get_settings()
    if settings.ipl_api_url is None or settings.ipl_api_key is None:
        raise IplApiConfigurationError("IPL API is not configured")
    return IplApiClient(
        base_url=str(settings.ipl_api_url),
        api_key=settings.ipl_api_key.get_secret_value(),
    )
