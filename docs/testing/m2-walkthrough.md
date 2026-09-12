# M2 Validation Evidence

The M2 Persistence Layer has been fully implemented and validated against the requirements.

## 1. Schema Generation and Review
- Models were exposed via `apps/api/app/infrastructure/models/__init__.py`.
- Alembic generated a single, deterministic migration (`m2_initial_schema`).
- **Migration manually reviewed**: Verified composite primary/foreign keys (`institution_id` scoping), custom check constraints (e.g., negative CGPA checks, overlapping constraints using GIST), enum validations, and default server timestamp implementations.
- Constraint names in `database.py` were adjusted (`column_0_N_name`) to prevent namespace collisions for composite keys.

## 2. Test Execution
Synthetic seed data and tests were created in `apps/api/tests/test_m2_persistence.py`, proving:
- **Repository Operations**: The persistence layer allows complex relationships and record insertions without leaking domain business logic.
- **Constraint Negatives**: Attempting to insert overlapping policy version activations correctly raises an `IntegrityError` due to PostgreSQL's exclusion constraints on time ranges using `btree_gist`.
- **Transaction Rollbacks**: Validated that `db_session.rollback()` clears partial state flawlessly.
- **Provenance Versioning**: Tested that source locators correctly maintain references (e.g., `doc_v1`) independently of status changes.

## 3. Fresh DB Rebuild & Determinism
- Initialized a completely fresh PostgreSQL instance.
- Applied `alembic upgrade head`.
- Successfully ran `alembic downgrade base` and `alembic upgrade head`.
- Triggered `alembic revision --autogenerate -m "check"`, which resulted in a `pass` implementation, confirming absolute zero schema drift and deterministic behavior.

> [!IMPORTANT]
> The evidence proves the database schema correctly isolates eligibility/business logic from persistence while strictly enforcing domain invariants. M2 is ready for independent review.
