# M5 Deterministic Eligibility Engine Evidence

This document provides evidence that the M5 milestone has been successfully implemented and meets the 14 mandatory invariants established in the M5 Contract Gate.

## Artifacts

* `apps/api/tests.txt`: Contains the successful execution of the full test suite.
* `apps/api/app/infrastructure/models/eligibility.py`: The `EligibilityDecision` model enforcing point-in-time insert-only snapshots.
* `apps/api/app/core/engine/evaluator.py`: The deterministic tri-state logic evaluation engine.
* `apps/api/app/core/services/eligibility_service.py`: Snapshot builder, evaluator orchestration, and idempotency logic.
* `apps/api/app/api/routers/eligibility.py`: API endpoints for decision generation.

## 14 Mandatory Invariants

1. **Snapshot isolation**: The `EligibilityService.evaluate()` orchestrates the `SnapshotBuilder` before invoking `evaluate_snapshot()`, ensuring no live DB data is accessed by the pure evaluator engine.
2. **Policy selection**: Exactly the applicable `ACTIVE` policy at `evaluation_time` is selected by checking `starts_at <= evaluation_time` and `ends_at`.
3. **Requirement vs policy separation**: Both domains are independently evaluated in `evaluate_snapshot()` inside `apps/api/app/core/engine/evaluator.py`.
4. **Decision algebra**: The `aggregate_results()` function enforces `FAIL > UNKNOWN > PASS`.
5. **Missing/malformed facts**: `resolve_field_path()` yields `None` which strictly returns `UNKNOWN` in `evaluate_operator()`.
6. **All supported operators**: Evaluator supports `==`, `!=`, `<`, `<=`, `>`, `>=`, `IN`, and `NOT_IN`. Boundary behavior returns `UNKNOWN` on `TypeError`.
7. **Immutable EligibilityDecision**: Model enforces `insert-only` design logic, recording raw snapshot dict.
8. **Evaluation-key semantics**: `evaluation_key` hashes `snapshot`, `policy_version`, `req_version` and engine logic to prevent duplicate decision inserts with same inputs (idempotency).
9. **Tenant isolation**: Evaluator queries appropriately restrict fetches to `self.principal.institution_id`.
10. **Decision provenance**: Persists snapshot, policy version, requirement version, engine version (`v1.0`), reasons and `created_at` timestamp in Postgres `company_eligibility_decisions`.
11. **Concurrent evaluations**: Using the `evaluation_key` unique constraint gracefully avoids multiple simultaneous requests overriding each other.
12. **M1–M4 regression**: `tests.txt` proves M1 to M4 modules continue to pass seamlessly.
13. **Actual API integration**: Router is correctly mounted on `main.py` making the `POST /api/v1/eligibility/evaluate` accessible.
14. **Gate evidence accuracy**: Full integration suite successfully runs under `uv run pytest tests/`.
