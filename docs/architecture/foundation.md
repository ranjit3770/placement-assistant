# M1 foundation

Browser → Nginx → Next.js or FastAPI. FastAPI owns public health/readiness and
versioned `/api/v1` routes. Database clients live in infrastructure. Lifespan owns
connection creation/cleanup; imports do not open connections.

`/health` is process liveness. `/ready` concurrently probes PostgreSQL, Redis and
Qdrant with bounded timeouts and sanitized up/down states. PostgreSQL failure is
HTTP 503. Redis/Qdrant failure is HTTP 200 with degraded=true: these services must
not disable a future deterministic eligibility endpoint (SRS §§47–48). The Compose
smoke gate separately requires ALL dependencies up. OpenAI is not probed or called.

The worker emits an expiring Redis heartbeat and handles shutdown. It has no jobs
yet; imports and ingestion are later milestones. Alembic is configured with empty
domain metadata; no domain tables or migrations are claimed in M1.

JWT verification has a protected `/api/v1/auth/me` boundary. User management,
login, authorization repositories and application endpoints are subsequent work.
The UI labels planned capabilities and uses real readiness rather than mock data.

Implementation references:
- [FastAPI lifespan](https://fastapi.tiangolo.com/advanced/events/)
- [Next.js App Router setup](https://nextjs.org/docs/app/getting-started/installation)
- [Compose dependency startup](https://docs.docker.com/compose/how-tos/startup-order/)
