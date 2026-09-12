# Implementation scope and decisions

Baseline: supplied SRS v2 and roadmap v2. The original documents are preserved.
Status: M0 ACCEPTED baseline; M1 ACCEPTED (foundation scope), per the project
coordinator's 2026-09-12 direction. M2 IN_PROGRESS — Domain Model + ERD.
This acceptance does not certify business functionality or production readiness.

## Accepted increment: M1 platform foundation

Deliver Next.js App Router/TypeScript/Tailwind, FastAPI/Pydantic, SQLAlchemy and
Alembic setup, PostgreSQL, Redis, Qdrant, worker heartbeat, Nginx, Docker Compose,
configuration, request logging, safe errors, health/readiness, JWT verification,
CI and automated negative tests. No student data or eligibility claims in the UI.

M2 introduces domain migrations; M3 requirements; M4 policy approval/activation;
M5 deterministic evaluation and replay. RAG and OpenAI begin at M6 and later.
No API key is needed for this increment. R0 authentication is only a verification
boundary so far: login, persisted users, revocation, and scoped RBAC remain pending.

## Conflicts and decisions still required before affected work

1. SRS §95 calls R4 Administrative Intelligence; roadmap §42 calls R4 Production
   Release. Preserve both labels pending a release-scope decision. M1 is unaffected.
2. SRS §23 mentions REVIEW_REQUIRED but §25 permits exactly three decisions.
   Proposed resolution: REVIEW_REQUIRED is workflow metadata; UNKNOWN is the
   decision. Do not introduce a fourth primary decision.
3. SRS §13 prohibits definitive decisions with missing mandatory requirements;
   §33 does not specify precedence of FAIL versus UNKNOWN. Proposed contract:
   unresolved mandatory inputs/policy definitions yield UNKNOWN; only a complete
   evaluable mandatory rule set can produce ELIGIBLE or NOT_ELIGIBLE. Confirm
   this interpretation before M5 implementation.
4. The coordinator confirmed highest valid accepted offer, one approved dream
   company/year with pre-announcement timing, and exact annual INR total CTC as
   the initial domain baseline. See [confirmed M2 decisions](m2-decisions.md).
   These are not ACTIVE policy; exceptions still require policy authorization.
5. SGPA semester selection, diploma/HSC alternatives, grading scale conversions,
   historical backlog metrics and unresolved compensation conversions require
   explicit policy definitions. Initial non-comparable packages remain unresolved.

Baseline acceptance does not resolve every later institutional interpretation.
Keep remaining choices explicit in the affected M3–M5 contracts.

## Current increment: M2 domain and database

Domain Model + ERD and the three confirmed baseline choices are now documented.
Next: physical PostgreSQL schema, SQLAlchemy models, Alembic migrations, scoped
repositories, reference seeds and database/recovery verification. No M2 migration
has been applied. Keep eligibility logic out of ORM models, and use isolated test
databases for rebuild validation. See [M2 plan](../testing/m2-plan.md).
