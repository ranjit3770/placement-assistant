# M2 Final Gate Evidence

This document contains the independent validation evidence for the final M2 package. All command outputs are preserved locally in this directory.

## Blocking Findings Remediation (B01–B06)

### B01: Tenant-Scoped Repositories
- **Implementation:** `BaseRepository.__init__` mandates `institution_id`. All reads filter on this tenant implicitly. Unrestricted updates are removed.
- **Test Result:** `test_tenant_isolation_reads` PASSED. (See `tests.txt`)

### B02: Append-Only Event History
- **Implementation:** Postgres trigger `enforce_append_only_history()` raises an exception on `UPDATE` or `DELETE` for historical event logs.
- **Test Result:** `test_append_only_event_protection` PASSED. (See `tests.txt`)

### B03: Published/Active Definition Immutability
- **Implementation:** Triggers protect core fields (like `definition`) in `policy_versions` when the status is `APPROVED`.
- **Test Result:** `test_active_definition_immutability` PASSED. (See `tests.txt`)

### B04: Concurrent Dream-Company Approval Limit
- **Implementation:** Handled via unique constraint in the `active_dream_approvals` projection table to defend against concurrent transactions.
- **Test Result:** `test_concurrent_dream_approval_limit` PASSED. (See `tests.txt`)

### B05: Comprehensive Invariant and Negative Tests
- **Implementation:** Negative test cases explicitly check DB constraint validations and throw `pytest.raises(ProgrammingError/IntegrityError)`.
- **Test Result:** All tests PASSED. (See `tests.txt`)

### B06: Backup/Restore Validation
- **Implementation:** Custom bash script that performs full backup/restore and schema/data equivalence checks.
- **Test Result:** Backup/Restore Validation SUCCESSFUL. Data row counts and hashes match perfectly. (See `backup-restore.txt`)

---

## Final Remediation Pass (R7–R10)

### R7: Migration Reversibility
- **Action:** Upgraded to `head`, downgraded to `base`, and upgraded back to `head` on a fresh database.
- **Result:** Successfully reversed all schema and trigger modifications with no errors. No metadata drift detected by `alembic check`. (See `migration.txt`)

### R8: Child Graph Immutability
- **Action:** Triggers now protect child records (`PolicyRule`, `RequirementCriterion`, `RequirementMember`) from `INSERT/UPDATE/DELETE` when parent definitions are `APPROVED` or `published`.
- **Result:** Reflected in successful schema migrations and verified by integration tests. (See `tests.txt` and `migration.txt`)

### R9: Child Immutability Negative Tests
- **Action:** `test_active_definition_immutability` and `test_published_requirement_immutability` attempt to mutate child elements of published roots.
- **Result:** Tests correctly throw Exceptions matching DB constraints. (See `tests.txt`)

### R10: Deterministic Backup Validation
- **Action:** The validation script now utilizes dynamic primary keys mapped from `pg_index` and orders canonical text hashes perfectly. Checks are fully stripped of cosmetic `pg_dump` deviations.
- **Result:** Deterministic hashes strictly identically match across all tables between `test` and `test_restore`. (See `backup-restore.txt`)

## Complete Git Status
- **Result:** Clean directory, changes safely persisted. (See `git.txt`)
