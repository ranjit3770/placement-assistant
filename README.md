# Placement Intelligence

M1–M5 are certified and frozen. M5 provides deterministic eligibility, immutable
decisions and snapshot replay; its certified commit and evidence caveat are in the
[M5 certification record](docs/project-status/m5.md).

Start with [onboarding](docs/ONBOARDING.md). M6 is now in a separate
[RAG contract/design gate](docs/contracts/rag-contract.md), consuming the certified
foundation. RAG implementation and AI-generated explanations are not yet delivered.

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
uses Python 3.12; local checks also support 3.14. Domain and eligibility Alembic
revisions exist. Inspect the target with `docker compose exec backend alembic current`;
do not reset certified development data to run fresh-database tests.

For host development, configure DATABASE_URL (`postgresql+psycopg`), REDIS_URL,
QDRANT_URL and JWT_SECRET explicitly, then run `uv run uvicorn app.main:create_app
--factory --reload`. The default Compose network does not publish database ports.
Use the Compose web shell for integrated `/ready` routing; standalone `npm run dev`
requires a reverse proxy to route health/API requests to FastAPI.

## Current boundaries

JWT verification is available at `/api/v1/auth/me`; the eligibility endpoint is
`POST /api/v1/eligibility/evaluate`. M2–M5 provide persistence, company/requirement
management, policy lifecycle and deterministic decisions. Certification is scoped
to the pinned evidence, not a claim of complete student-facing product readiness.
M6 adds document preservation, Qdrant retrieval and verified citations through
new interfaces. It cannot activate rules or modify M5 decisions.

This is a local development deployment. Production TLS, hardened database roles,
rate limits, backup/restore, full authorization and independent acceptance remain
required. See [validation evidence](docs/testing/m1-validation.md).
