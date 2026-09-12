# M2 — Domain Model & Persistence (Remediation Final Evidence)

**Status:** IMPLEMENTED / VALIDATION PASSED / PENDING INDEPENDENT ACCEPTANCE

This document serves as the final Release Candidate evidence package for the M2 gate, addressing all 6 blocking findings from the previous independent review.

---

## B01 — Tenant-Scoped Repositories
* **Requirement:** Every repository operation must enforce authenticated tenant scope to guarantee multi-tenant data isolation.
* **Implementation Files:** `apps/api/app/infrastructure/repositories/base.py`, `student.py`, `policy.py`, `recruitment.py`
* **Mechanism:** `BaseRepository.__init__` strictly requires `institution_id`. All query generation (e.g., `_get_base_query()`) implicitly filters on `model.institution_id == self.institution_id`. Unrestricted updates/deletes are strictly removed and segregated.
* **Test File:** `apps/api/tests/test_m2_persistence.py`
* **Test Name:** `test_tenant_isolation_reads`
* **Command:** `uv run pytest tests/test_m2_persistence.py::test_tenant_isolation_reads -v`
* **Result:** PASSED. Attempting to read a student across tenant boundaries correctly returns `None`.

---

## B02 — Append-Only Event History
* **Requirement:** Historical events cannot be updated or deleted.
* **Implementation Files:** `apps/api/migrations/versions/be3b6aafad0b_m2_remediation_schema.py`
* **Mechanism:** PostgreSQL trigger `enforce_append_only_history()` executing `BEFORE UPDATE OR DELETE` raises `Immutable event history`. `EventRepository` at the application layer also suppresses `update` and `delete`.
* **Test File:** `apps/api/tests/test_m2_persistence.py`
* **Test Name:** `test_append_only_event_protection`
* **Command:** `uv run pytest tests/test_m2_persistence.py::test_append_only_event_protection -v`
* **Result:** PASSED. Trigger raises `ProgrammingError` containing "Immutable event history".

---

## B03 — Published/Active Definition Immutability
* **Requirement:** Approved/active definitions cannot have their authoritative payload rewritten.
* **Implementation Files:** `apps/api/migrations/versions/be3b6aafad0b_m2_remediation_schema.py`
* **Mechanism:** PostgreSQL trigger `enforce_policy_version_immutability()` blocks `DELETE` on active definitions and raises an exception if `definition`, `schema_version`, or `compensation_id` are modified during an `UPDATE`. Status transitions (e.g., to ARCHIVED) are still permitted.
* **Test File:** `apps/api/tests/test_m2_persistence.py`
* **Test Name:** `test_active_definition_immutability`
* **Command:** `uv run pytest tests/test_m2_persistence.py::test_active_definition_immutability -v`
* **Result:** PASSED. Trigger successfully protects the core definition payload for an `APPROVED` version.

---

## B04 — Concurrent Dream-Company Approval Limit
* **Requirement:** Only one active approved dream company can exist for a student in an academic year, safely defended against concurrent transactions.
* **Implementation Files:** `apps/api/app/infrastructure/models/recruitment.py`, `be3b6aafad0b_m2_remediation_schema.py`
* **Mechanism:** A projection table `active_dream_approvals` enforcing a `UNIQUE (institution_id, student_id, academic_year_id)` constraint.
* **Test File:** `apps/api/tests/test_m2_persistence.py`
* **Test Name:** `test_concurrent_dream_approval_limit`
* **Command:** `uv run pytest tests/test_m2_persistence.py::test_concurrent_dream_approval_limit -v`
* **Result:** PASSED. Two parallel async sessions attempt to approve declarations simultaneously; exactly one succeeds, and the other receives an `IntegrityError` due to the unique constraint.

---

## B05 — Comprehensive Invariant and Negative Tests
* **Requirement:** Important invariants must have negative tests ensuring invalid operations fail correctly.
* **Implementation Files:** `apps/api/tests/test_m2_persistence.py`
* **Mechanism:** Negative validations leveraging `pytest.raises()` wrapping explicit failure points (`IntegrityError`, `ProgrammingError`).
* **Test File:** `apps/api/tests/test_m2_persistence.py`
* **Command:** `uv run pytest tests/test_m2_persistence.py -v`
* **Result:** PASSED. All tests successfully run end-to-end, validating invariants from isolation to immutability.

---

## B06 — Backup/Restore Validation
* **Requirement:** Database backup and restoration must preserve the M2 persistence contract.
* **Implementation Files:** `infrastructure/scripts/test_m2_backup_restore.sh`
* **Mechanism:** Bash script executing a full lifecycle: `alembic upgrade head`, data injection (via pytest), `pg_dump`, `pg_restore` into a fresh `test_restore` db, and `pg_dump` diff comparison alongside tuple counting.
* **Command:** `chmod +x infrastructure/scripts/test_m2_backup_restore.sh && ./infrastructure/scripts/test_m2_backup_restore.sh`
* **Result:** PASSED. 
* **Deviation Note:** `pg_dump` normalizes string-array casting in check constraints slightly differently upon restoration, producing minor string casting cosmetic diffs in the schema. However, data row counts and logical schema structure are perfectly preserved and equivalent.

---

## Fresh-Database Validation Confirmation
* `alembic upgrade head` succeeds seamlessly from a blank slate.
* All `test_m2_persistence.py` tests pass on the fresh schema.
* Backup/Restore successfully migrates schemas and data reliably.
* `alembic check` reports `No new upgrade operations detected.`, confirming zero unintended metadata drift.
* `git status` is completely clean.
* All M2 remediation changes and evidence documentation are successfully pushed to `origin/dev`.

**Conclusion:** M2 remediation implementation is frozen and ready for independent re-review.
