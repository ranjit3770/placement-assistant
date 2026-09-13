# M3 Certification Evidence

This package contains the implementation artifacts and negative test results demonstrating that the M3 API layer securely respects the M2 persistence boundaries and domain invariants.

## M2 Dependencies Consumed
- Tenant repositories (`BaseRepository` scoping)
- Append-only event repositories (`EventRepository`)
- Definition immutability (PostgreSQL triggers mapped to `400 INVALID_OPERATION`)
- Check constraints (mapped to `409 CONFLICT`)

## M3 Targeted Verification Results

1. **Tenant Isolation**: Cross-tenant API requests effectively returned `404 NOT_FOUND` for existing entities in other tenants, preventing information leakage.
2. **Company Revision History**: API correctly preserved versions 1, 2, and 3 sequentially as verified by direct DB state assertions.
3. **Company-Role Ownership**: The `OpportunityService` correctly rejected invalid cross-company Role usage with `409 CONFLICT` using domain logic, without relying purely on FK failures.
4. **Opportunity Lifecycle Idempotency**: `close_opportunity` successfully returned `200 OK` on idempotency checks (`CLOSED` -> `CLOSED`).
5. **Requirement Transaction Rollback**: Transactions containing CHECK violations aborted atomically, leaving no dangling `Requirement` or `RequirementVersion` data in the DB.
6. **Published Version Immutability**: Graph mutations on `PUBLISHED` versions correctly tripped the `psycopg.errors.RaiseException` immutability trigger and successfully mapped to a `400 INVALID_OPERATION` API response without returning a 500.

### 100% Passing Test Suite
Output recorded in `tests.txt`.
