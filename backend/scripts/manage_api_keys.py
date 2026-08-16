#!/usr/bin/env python3
import argparse
import asyncio
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.security.api_keys import ApiClient, ApiKeyRegistry
from app.security.postgres_admin import PostgresApiKeyAdmin


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage AI Query Engine public API keys")
    parser.add_argument("--backend", choices=["local", "postgres"], default="local")
    parser.add_argument("--file", default=".data/api_clients.json", help="Client registry path")
    parser.add_argument("--database-url", help="Overrides DATABASE_URL for postgres backend")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="Create a client and show its key once")
    create.add_argument("--name", required=True)
    create.add_argument("--rpm", type=int, default=10, help="Requests per minute")

    commands.add_parser("list", help="List clients without revealing key hashes")
    revoke = commands.add_parser("revoke", help="Revoke a client")
    revoke.add_argument("client_id")
    return parser


async def run_postgres(args: argparse.Namespace) -> None:
    database_url = args.database_url or get_settings().database_url
    engine = create_async_engine(database_url, pool_pre_ping=True)
    admin = PostgresApiKeyAdmin(engine)
    try:
        if args.command == "create":
            client, api_key = await admin.create(args.name, args.rpm)
            print(f"Client ID: {client.id}")
            print(f"API key (shown once): {api_key}")
        elif args.command == "list":
            for client in await admin.list():
                print_client(client)
        elif not await admin.revoke(args.client_id):
            raise SystemExit(f"Unknown or already revoked client: {args.client_id}")
        else:
            print(f"Revoked {args.client_id}")
    finally:
        await engine.dispose()


def print_client(client: ApiClient) -> None:
    status = "active" if client.active else "revoked"
    print(
        f"{client.id}\t{client.name}\t{status}\t"
        f"{client.requests_per_minute} rpm\t{client.key_prefix}..."
    )


def run_local(args: argparse.Namespace) -> None:
    registry = ApiKeyRegistry(Path(args.file))
    if args.command == "create":
        client, api_key = registry.create(args.name, args.rpm)
        print(f"Client ID: {client.id}")
        print(f"API key (shown once): {api_key}")
    elif args.command == "list":
        for client in registry.load():
            print_client(client)
    elif not registry.revoke(args.client_id):
        raise SystemExit(f"Unknown client: {args.client_id}")
    else:
        print(f"Revoked {args.client_id}")


def main() -> None:
    args = build_parser().parse_args()
    if args.backend == "postgres":
        asyncio.run(run_postgres(args))
    else:
        run_local(args)


if __name__ == "__main__":
    main()
