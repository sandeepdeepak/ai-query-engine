import hashlib
import json
import secrets
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field


class ApiClient(BaseModel):
    id: str
    name: str
    key_prefix: str
    key_hash: str
    active: bool = True
    requests_per_minute: int = Field(default=10, ge=1, le=10_000)
    created_at: datetime


class ApiKeyRegistry:
    def __init__(self, path: Path) -> None:
        self.path = path

    @staticmethod
    def hash_key(api_key: str) -> str:
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_key(environment: str = "live") -> str:
        return f"aqe_{environment}_{secrets.token_urlsafe(32)}"

    def authenticate(self, api_key: str) -> ApiClient | None:
        supplied_hash = self.hash_key(api_key)
        for client in self.load():
            if client.active and secrets.compare_digest(client.key_hash, supplied_hash):
                return client
        return None

    def load(self) -> list[ApiClient]:
        if not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return [ApiClient.model_validate(item) for item in payload]

    def save(self, clients: list[ApiClient]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps([item.model_dump(mode="json") for item in clients], indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def create(self, name: str, requests_per_minute: int = 10) -> tuple[ApiClient, str]:
        api_key = self.generate_key()
        client = ApiClient(
            id=f"client_{secrets.token_hex(8)}",
            name=name,
            key_prefix=api_key[:18],
            key_hash=self.hash_key(api_key),
            requests_per_minute=requests_per_minute,
            created_at=datetime.now(UTC),
        )
        clients = self.load()
        clients.append(client)
        self.save(clients)
        return client, api_key

    def revoke(self, client_id: str) -> bool:
        clients = self.load()
        found = False
        for client in clients:
            if client.id == client_id:
                client.active = False
                found = True
        if found:
            self.save(clients)
        return found
