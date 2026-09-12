# M1 validation record

Date: 2026-09-12. Status: ACCEPTED — foundation scope, per the project coordinator's
subsequent milestone assessment. This records acceptance of the existing evidence;
it does not claim an independent production audit.

Scope: foundation configuration, backend health/error/authentication boundaries,
frontend build, Compose infrastructure and negative dependency tests.

| Check | Result |
| --- | --- |
| API tests, Python 3.14 | 18 passed |
| Ruff lint and format, API and infrastructure scripts | Passed |
| Strict mypy, API | Passed (10 source files) |
| ESLint, Prettier and TypeScript, web | Passed |
| Next.js production build, local and Docker | Passed |
| npm dependency audit during installation | 0 known vulnerabilities reported |
| Compose configuration | Passed |
| Docker images: backend, worker, frontend | Built successfully |
| Seven-service `docker compose up -d --wait` | Passed |
| Public reverse-proxy smoke test | Passed |
| PostgreSQL, Redis and Qdrant readiness probes | All up |
| Worker heartbeat health check | Passed |
| `docker compose exec -T backend alembic current` | Passed; no domain revisions yet |
| Chromium desktop/mobile browser tests | 4 passed |

The browser tests verify rendering, live connection status, viewport overflow,
absence of uncaught page errors, dependency-error display and successful retry.
API negatives cover expired/invalid/tampered tokens, issuer/audience/role/identity,
missing expiry, anonymous access, dependency timeouts, database failure, optional
service degradation, sanitized errors and disabled production API docs.

Running local URL: http://localhost:18081. Existing services occupied 8080 and
18080; their containers were not modified. The ignored local `.env` uses 18081.
The template remains 8080; `make smoke` follows the configured HTTP_PORT.
Only Nginx is published, on loopback. Generated `.env` permissions verified: 0600.

Reproduce:

```sh
make up
make smoke
cd apps/web
SMOKE_URL=http://127.0.0.1:18081 npm run test:e2e
```

Install Chromium with `npx playwright install chromium` if it is not available.
This session used the existing browser cache at `/tmp/placement-playwright`.

Non-blocking tool warnings: the installed Starlette test client reports httpx and
AnyIO deprecations; ESLint 9 reports end of support. These did not fail the checks.
Docker could not capture Git provenance: this workspace has no initialized Git
repository. No commit or remote CI run is claimed. CI is configured, not executed
on a hosted runner. Python 3.12 was exercised by the container runtime; unit tests
were run locally on Python 3.14, with the CI job targeting 3.12.

Detailed contract decisions, M2 domain migrations, full login/RBAC, eligibility, RAG,
agent, production security, accessibility audit, performance/recovery validation
and independent gate review remain outstanding. Browser smoke checks are not a
complete accessibility or product-acceptance audit.
