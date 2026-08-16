# Render + Supabase Postgres deployment

This deployment keeps the tested FastAPI/SQLGlot query engine on Render and stores partner
clients, rate windows, and usage audits in a Supabase Postgres project you own.

## 1. Create the private database objects

Open the Supabase SQL Editor for your own project and run:

[`infra/supabase/api_access.sql`](infra/supabase/api_access.sql)

The script creates the non-exposed `api_private` schema. It enables RLS and revokes access from
`public`, `anon`, and `authenticated`. It also creates a no-login `api_query_engine` capability
role with only the table operations required by the backend.

Create a dedicated login with a generated password and grant it the capability role, replacing
the placeholder before running it:

```sql
create role api_query_engine_login login password 'GENERATE_A_LONG_RANDOM_PASSWORD';
grant api_query_engine to api_query_engine_login;
```

Use that login for Render instead of the `postgres` database owner. The backend connects directly
to Postgres; no Supabase secret/service-role key is used by FastAPI.

The IPL publishable key alone cannot apply this script. You need project-owner SQL Editor or
database access. The IPL data project and the API-management project may be different projects.

## 2. Configure the pooled database URL

Build the transaction-pooler connection string for `api_query_engine_login` using the host and
project identifier shown by Supabase **Connect**, then change its scheme for SQLAlchemy asyncpg:

```text
postgresql+asyncpg://API_QUERY_ENGINE_LOGIN:PASSWORD@POOLER_HOST:6543/postgres
```

Set it as `DATABASE_URL`. The backend disables asyncpg's prepared-statement cache for transaction
pooler compatibility and maintains a bounded 5+5 application connection pool.

For local activation in the root `.env`:

```text
PUBLIC_API_ACCESS_BACKEND=postgres
DATABASE_URL=postgresql+asyncpg://...
```

## 3. Create partner keys in Supabase

After the SQL script and root `.env` are configured:

```bash
make api-key-create-postgres NAME="Partner Name" RPM=10
make api-key-list-postgres
make api-key-revoke-postgres CLIENT_ID="client_..."
```

Only a SHA-256 digest of each high-entropy key is stored. The plaintext key is shown once.

## 4. Deploy Render Blueprint

Commit the repository to a Git provider and create a Render Blueprint using
[`render.yaml`](render.yaml). Provide these secret values in Render:

- `DATABASE_URL` — owned Supabase project's transaction-pooler URL using the
  `postgresql+asyncpg` scheme
- `OPENAI_API_KEY`
- `IPL_API_URL`
- `IPL_API_KEY`
- `FRONTEND_ORIGIN`

The Blueprint already sets `PUBLIC_API_ACCESS_BACKEND=postgres`, uses the backend Dockerfile,
and checks `/api/v1/health`. No persistent Render disk is required.

## 5. Verify after deployment

```bash
curl "https://YOUR_RENDER_HOST/api/v1/health"

curl -X POST "https://YOUR_RENDER_HOST/public/v1/query" \
  -H "X-API-Key: aqe_live_..." \
  -H "Content-Type: application/json" \
  -d '{"question":"Show the last 2 RCB matches from 2026","max_rows":20}'
```

Confirm `X-Request-ID`, `X-RateLimit-Limit`, and `X-RateLimit-Remaining` response headers. In
Supabase, confirm rows appear in `api_private.api_rate_windows` and `api_private.api_usage`.

## Operational notes

- Rate limiting uses atomic one-minute fixed windows shared by every Render instance.
- Audit records store a question digest, not the natural-language question.
- Periodically delete rate windows older than one day; an example statement is included in the
  SQL script.
- Free Render services can sleep after inactivity, but authentication data remains in Supabase.
- Do not expose Supabase database credentials, OpenAI keys, or IPL credentials to React or API
  consumers.
