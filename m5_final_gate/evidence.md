# M5 Final Gate Evidence — Deterministic Eligibility Engine

## Suite Result

```
57 passed, 0 failed, 0 errors
```

Full verbose output: `m5_final_gate/tests.txt`

## Test Breakdown by Milestone

| Milestone | Tests | Status |
|-----------|-------|--------|
| M1 Foundation | 18 | ✅ ALL PASS |
| M2 Persistence | 5 | ✅ ALL PASS |
| M3 API | 9 | ✅ ALL PASS |
| M4 Policy | 4 | ✅ ALL PASS |
| M5 Eligibility (unit) | 8 | ✅ ALL PASS |
| M5 Eligibility (integration) | 13 | ✅ ALL PASS |
| **Total** | **57** | **✅ ALL PASS** |

## M5 Invariant Verification

### 1. Policy Selection — `_get_active_policy()`
- Queries by: `institution_id`, `academic_year_id`, `scope`, `starts_at <= evaluation_time`, `ends_at > evaluation_time`, `status == ACTIVE`
- 0 matches → `NO_ACTIVE_POLICY` (HTTP 400)
- \>1 match → `POLICY_AMBIGUITY` (HTTP 500)
- Tested by: `test_active_policy_selection`, `test_no_active_policy`, `test_policy_activation_window`, `test_policy_scope_selection`

### 2. Policy vs Requirement Separation
- Policy rules: fetched from `PolicyRule` by `policy_version_id`
- Requirement criteria: fetched from `Criterion` by `requirement_version_id`
- Both are independent constraint domains evaluated separately in `evaluate_snapshot()`
- Tested by: `test_evaluate_snapshot_not_eligible_due_to_policy`, `test_evaluate_snapshot_not_eligible_due_to_req`

### 3. Authoritative Snapshot Construction
- CGPA derived from latest `AcademicRecord` with `cgpa_state == KNOWN`
- Open backlog count derived from latest `BacklogEvent.kind == OPENED`
- Active offer count derived from latest `OfferEvent.kind in (RECEIVED, ACCEPTED, TERMS_REVISED)`
- Tested by: `test_snapshot_uses_authoritative_facts`

### 4. Missing/Malformed Facts → UNKNOWN
- `cgpa = None` (state UNKNOWN) → criterion result `UNKNOWN`
- `FAIL > UNKNOWN > PASS` algebra applied correctly
- Tested by: `test_missing_authoritative_fact_becomes_unknown`, `test_evaluate_rule_unknown`

### 5. Decision Algebra: FAIL > UNKNOWN > PASS
- Unit tests: `test_aggregate_results`
- Integration: Any FAIL in either domain → `NOT_ELIGIBLE`
- No FAIL + any UNKNOWN → `UNKNOWN`
- All PASS → `ELIGIBLE`

### 6. Immutable Eligibility Decisions
- PL/pgSQL trigger `ensure_decision_immutability` on `eligibility_decisions` table
- `BEFORE UPDATE OR DELETE` → `RAISE EXCEPTION`
- Alembic migration `110b14c4b973`
- Tested by: `test_decision_immutability` (both UPDATE and DELETE blocked)

### 7. Evaluation Idempotency
- `evaluation_key = SHA256(snapshot_json | policy_version_id | req_version_id | engine_version)`
- Same inputs → same decision returned (no duplicate row)
- Tested by: `test_evaluation_idempotency`

### 8. Changed Inputs → New Decision
- Modifying CGPA between evaluations produces a different `evaluation_key` and distinct `decision.id`
- Tested by: `test_changed_inputs_create_new_decision`

### 9. Snapshot Isolation
- Pure function `evaluate_snapshot()` receives frozen dict, does not query DB
- Modifying live student data after snapshot creation does not alter the evaluation result
- Tested by: `test_engine_evaluates_domain_criteria_with_snapshot_isolation`, `test_snapshot_replay`

### 10. Snapshot Replay
- Persisted `snapshot`, `policy_rules`, `criteria` replayed through `evaluate_snapshot()` produce identical `result` and `reasons`
- Tested by: `test_snapshot_replay`

### 11. Concurrent Evaluation Safety
- Two independent ASGI apps with separate DB sessions evaluate same student/opportunity concurrently
- `IntegrityError` on duplicate `evaluation_key` is caught; existing decision returned
- Both requests return 201; exactly 1 row persisted
- Tested by: `test_concurrent_evaluation`

### 12. Evaluator Operators
- `==`, `!=`, `>`, `>=`, `<`, `<=`, `in`, `not_in`
- Tested by: `test_evaluate_rule_pass`, `test_evaluate_rule_fail`

### 13. AI Has Zero Authority
- No LLM call in the eligibility evaluation path
- `evaluate_snapshot()` is a pure deterministic function
- `EligibilityService.evaluate()` calls only DB queries and the pure evaluator
- The router `/api/v1/eligibility/evaluate` delegates entirely to `EligibilityService`

### 14. Error Code Propagation
- `HTTPException(status, {"code": ..., "message": ...})` propagated through `main.py` exception handler
- Custom codes (e.g. `NO_ACTIVE_POLICY`) preserved in `response.json()["error"]["code"]`

## Files Modified/Created

### New Files
- `app/core/engine/evaluator.py` — Pure deterministic tri-state evaluator
- `app/core/services/eligibility_service.py` — Policy selection, snapshot construction, evaluation orchestration
- `app/api/routers/eligibility.py` — FastAPI router
- `app/api/schemas/eligibility.py` — Pydantic request/response schemas
- `app/infrastructure/models/eligibility.py` — EligibilityDecision SQLAlchemy model
- `migrations/versions/110b14c4b973_eligibility_immutability.py` — Immutability trigger
- `tests/test_m5_eligibility.py` — 8 unit tests for evaluator
- `tests/test_m5_eligibility_integration.py` — 13 integration tests

### Modified Files
- `app/main.py` — Added eligibility router registration; improved HTTPException handler to propagate custom error codes
- `tests/test_m3_api.py` — Fixed pre-existing test isolation bug in `test_requirement_transaction_rollback` (unscoped query)

## M1–M4 Regression Status

No M1–M4 regressions. All 36 pre-existing tests continue to pass.
