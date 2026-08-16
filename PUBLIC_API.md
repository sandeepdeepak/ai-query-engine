# AI Query Engine Partner API

## Endpoint

```http
POST /public/v1/query
X-API-Key: aqe_live_...
Content-Type: application/json
```

Local base URL: `http://127.0.0.1:8001`

```bash
curl -X POST 'http://127.0.0.1:8001/public/v1/query' \
  -H 'X-API-Key: aqe_live_replace_me' \
  -H 'Content-Type: application/json' \
  -d '{
    "question": "Show the last 2 RCB matches from the 2026 season",
    "max_rows": 20
  }'
```

The response contains the generated SQL, validation plan, rows, execution metadata, and a
`request_id`. Response headers include:

- `X-Request-ID`
- `X-RateLimit-Limit`
- `X-RateLimit-Remaining`
- `X-API-Client`

Rate-limit failures return `429` with `Retry-After`.

## Errors

Public API errors use one stable envelope:

```json
{
  "error": {
    "code": "invalid_api_key",
    "message": "Invalid or revoked API key",
    "request_id": "req_..."
  }
}
```

Error codes include `invalid_api_key`, `invalid_request`, `unsafe_or_invalid_query`,
`rate_limit_exceeded`, and `upstream_failure`.

## Client key management

Run these from the repository root:

```bash
make api-key-create NAME="Partner name" RPM=10
make api-key-list
make api-key-revoke CLIENT_ID="client_..."
```

Never send a key in a URL or commit one to source control. Give every partner a different key
so it can be limited and revoked independently. The OpenAI and IPL credentials stay inside the
backend and must never be shared with API consumers.

## OpenAPI

- Swagger UI: `/docs`
- OpenAPI JSON: `/openapi.json`

The `public-api` section contains the partner operation and its authentication scheme.

## Production requirements

Local mode uses a JSON registry and in-memory limiter for development. Production mode sets
`PUBLIC_API_ACCESS_BACKEND=postgres` and uses the private Supabase schema described in
[`HYBRID_DEPLOYMENT.md`](HYBRID_DEPLOYMENT.md). In Postgres mode:

1. API clients contain only hashed credentials.
2. Atomic fixed-window counters are shared by all application instances.
3. Successful usage is audited without retaining question text.

Additional production controls:

1. Put FastAPI behind HTTPS and a managed load balancer/API gateway.
2. Store OpenAI and IPL credentials in a secret manager.
3. Restrict browser CORS to registered partner origins; server-to-server calls do not use CORS.
4. Add centralized audit logs keyed by `request_id` and `client_id` without logging questions if
   their contents may be sensitive.

Do not publish the endpoint without HTTPS. Rotate or revoke a client key immediately if it is
exposed.
