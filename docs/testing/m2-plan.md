# M2 implementation and verification plan

Status: IN_PROGRESS — Domain Model + ERD drafted; three domain choices confirmed.
No M2 models or migrations are implemented yet.

| Step | Deliverable | Status |
| --- | --- | --- |
| M2.1–M2.3 | Glossary, ownership, ERD | Drafted |
| Decision checkpoint | Offer, dream company, compensation | Confirmed baseline; not activated policy |
| M2.4 | Physical PostgreSQL schema | Pending |
| M2.5–M2.6 | SQLAlchemy models / Alembic | Pending |
| M2.7–M2.8 | Constraints, indexes, provenance/versioning | Designed; implementation pending |
| M2.9–M2.10 | Scoped repositories / reference seeds | Pending |
| M2.11–M2.12 | Tests / rebuild, rollback, recovery | Pending |

Required database tests:

- Empty PostgreSQL → Alembic upgrade → expected schema and indexes.
- Cross-institution child references fail; repositories cannot leak other tenants.
- Numeric/scale bounds, null-state combinations, money shape and comparable-value
  validation, unique revisions and idempotent imported events.
- Concurrent dream approvals enforce configured limits; revisions/activation serialize.
- Multiple truthful offers remain storable; unknown package is not absent offer.
- Published requirements and active definitions resist update/delete; conflicting
  activation intervals are rejected in identical applicability scope.
- Consistent snapshots under concurrent updates; atomic persistence and immutable
  completed checks, evidence and criterion results.
- Provenance survives corrections/imports. Reference seeds are idempotent and
  contain no real students, credentials or invented active policies.

Recovery validation uses an isolated test Compose project and dedicated volumes;
never `down -v` on the working M1 stack. Migrate a clean database, load synthetic
history fixtures, exercise downgrade/upgrade and document irreversible steps.
Back up and restore into a second empty database; compare schema, rows, event
chains and snapshot hashes. Record drift checks and exact execution evidence.

M2 proves storage can support replay; the replay algorithm belongs to M5. Acceptance
requires all applicable model/migration/repository/recovery evidence, not merely an
ERD. Explicitly record any deferred catalog tables, including detailed agent tables.
