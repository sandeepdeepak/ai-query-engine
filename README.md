# AI Query Engine

Natural language to validated SQL to structured data, with a React interface that exposes every processing stage.

## Phase 1 foundation

- React, TypeScript, and Vite frontend
- FastAPI backend with typed configuration
- PostgreSQL connection pool and readiness check
- Backend-only adapter for the public IPL Supabase REST API
- Docker Compose local environment
- Backend and frontend baseline tests
- Cached metadata catalog for verified IPL resources
- React Schema Explorer for tables, columns, keys, and types
- Provider-based natural-language-to-SQL generation with structured output
- Full React result workbench with sortable data, SQL/validation inspection, and CSV/JSON export

## Run with Docker

```bash
cp .env.example .env
docker compose up --build
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API docs: http://localhost:8000/docs
- Liveness: http://localhost:8000/api/v1/health
- Database readiness: http://localhost:8000/api/v1/health/ready
- IPL API readiness: http://localhost:8000/api/v1/health/data-source
- Schema catalog: http://localhost:8000/api/v1/schema
- Live schema verification: http://localhost:8000/api/v1/schema/verify
- SQL generation: `POST http://localhost:8000/api/v1/sql/generate`
- SQL validation: `POST http://localhost:8000/api/v1/sql/validate`
- Full query workflow: `POST http://localhost:8000/api/v1/query`
- Protected partner API: `POST http://localhost:8000/public/v1/query`
- Protected partner schema: `GET http://localhost:8000/public/v1/schema`

Set `AI_PROVIDER=mock` for deterministic local development. To use OpenAI, set
`AI_PROVIDER=openai` and provide `OPENAI_API_KEY`; the key remains backend-only.

The IPL publishable key is read from `.env`. It is never required by the React bundle.

## Third-party API

The partner endpoint requires a unique `X-API-Key`, applies a per-client requests-per-minute
limit, and returns request/rate-limit headers. Create a local client key with:

```bash
make api-key-create NAME="Example Partner" RPM=10
```

The plaintext key is shown once; only its SHA-256 digest is persisted. See
[`PUBLIC_API.md`](PUBLIC_API.md) for the contract, examples, key revocation, and production
deployment requirements.

For stateless Render hosting backed by Supabase Postgres, follow
[`HYBRID_DEPLOYMENT.md`](HYBRID_DEPLOYMENT.md). The included `render.yaml` Blueprint and private
Supabase SQL script cover deployment, shared rate limiting, partner keys, and usage auditing.

## Run tests locally

Backend dependencies:

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/pytest
```

Frontend dependencies:

```bash
cd frontend
npm install
npm test -- --run
```

## Planned phases

1. Foundation
2. Schema metadata service
3. AI-to-SQL generation
4. SQL validation and read-only execution
5. Query workspace UI
6. Streaming progress and query history
7. Security, evaluation, CI, and deployment
