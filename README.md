# Placement Intelligence

Implementation begins with the platform foundation in [the roadmap](docs/roadmap.md),
using [SRS v2](docs/srs.md). This preview does not yet evaluate students or use AI.
See [scope and unresolved decisions](docs/contracts/release-scope.md).

M1 is accepted for foundation scope. M2 has started with the
[Domain Model](docs/contracts/domain-model.md), [ERD](docs/architecture/domain-erd.md)
and [confirmed domain decisions](docs/contracts/m2-decisions.md).
Models, migrations and database validation are the next M2 deliverables.

## Run the development stack

Requires Docker Engine and Docker Compose v2, plus Python 3 for configuration.

```sh
make configure
make up
make smoke
```

Open http://localhost:8080. API docs: http://localhost:8080/api/v1/docs.
The current workspace is running on **http://localhost:18081** because 8080 and
18080 were already occupied; its local `.env` records that port.
`make configure` creates `.env` with random development secrets and preserves any
existing file. Set HTTP_PORT in `.env` if 8080 is occupied. `make smoke` reads that
port automatically; `SMOKE_URL` can override the full URL.

Seven services: Nginx, frontend, backend, worker, PostgreSQL, Redis, Qdrant.
Only Nginx is exposed, on loopback. `make down` stops this stack and retains data
volumes. No credentials or OpenAI key are needed from a real institution.

## Development checks

Python 3.12–3.14, uv, Node.js 24 and npm:

```sh
cd apps/api
uv sync --frozen
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run mypy
cd ../web
npm ci
npm run lint
npm run build
npm run typecheck
npx playwright install chromium
SMOKE_URL=http://127.0.0.1:8080 npm run test:e2e
```

`uv.lock` and `package-lock.json` pin resolved dependencies. The API Docker image
uses Python 3.12; local checks also support 3.14. Alembic is scaffolded for M2:
`docker compose exec backend alembic current`. There are no domain revisions yet.

For host development, configure DATABASE_URL (`postgresql+psycopg`), REDIS_URL,
QDRANT_URL and JWT_SECRET explicitly, then run `uv run uvicorn app.main:create_app
--factory --reload`. The default Compose network does not publish database ports.
Use the Compose web shell for integrated `/ready` routing; standalone `npm run dev`
requires a reverse proxy to route health/API requests to FastAPI.

## Current boundaries

JWT verification is available at `/api/v1/auth/me`; login and persisted users are
not implemented. There is no eligibility endpoint or fabricated student data.
M2–M5 deliver domain models, approved requirements/policies, decisions and replay.
M6+ adds Qdrant retrieval and OpenAI integration. No institutional business defaults
have been silently activated.

This is a local development deployment. Production TLS, hardened database roles,
rate limits, backup/restore, full authorization and independent acceptance remain
required. See [validation evidence](docs/testing/m1-validation.md).
