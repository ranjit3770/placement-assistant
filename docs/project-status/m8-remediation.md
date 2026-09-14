# M8 remediation checkpoint — 2026-09-14

Status: **NOT CERTIFIED / IN PROGRESS**. M9 remains LOCKED.
M1–M7 retain their recorded CERTIFIED / FROZEN status.
This is an implementation progress note, not a regenerated evidence package.

## First remediation slice: M5 authority

- M8 installs an asynchronous real-M5 adapter in a request-local registry copy.
  It does not mutate the frozen M7 registry or call its conceptual eligibility stub.
- The injected application session resolves the student using authenticated
  institution and `Student.user_id`, not a caller-supplied student ID or JWT subject
  treated as a student ID. M8 conversation ownership uses the same mapping.
- The adapter resolves exactly one published, currently activated requirement
  version belonging to the opportunity and institution. Missing/ambiguous context
  fails closed; it does not select an arbitrary version or return stub eligibility.
- The frozen `EligibilityService.evaluate` supplies the persisted decision. M8
  returns its ID, evaluation key, reasons, snapshot, engine version and policy/
  requirement references in `authoritative_decision` without recomputing them.
- Final messages use a deterministic fallback derived from that decision. Unchecked
  model text is neither returned nor persisted as an assistant explanation. Without
  an authoritative decision, the message states that eligibility is unverified.
- A new evaluation attempt clears any earlier result, including malformed or
  budget-rejected attempts. Conversation history cannot supply decision authority.
- Returned evidence is temporarily empty; conceptual M7 policy-tool output is not
  represented as verified M6 evidence. Real M6 integration remains pending.

## Verification performed

New tests exercise missing database fail-closed behavior, unsupported LLM claims,
and an actual PostgreSQL/M5 evaluation with contradictory persisted conversation
history and contradictory LLM output. They compare response provenance with the
saved `EligibilityDecision` and verify repeat evaluation returns the same record.
Only model responses are mocked in the real-M5 test; memory, student resolution,
requirement selection, evaluation and decision persistence use PostgreSQL.

Final combined run: **166 passed, 0 skipped, 5 warnings in 12.37s**.
Both `M6_TEST_DATABASE_URL` and `M8_TEST_DATABASE_URL` pointed to the dedicated
PostgreSQL test database on port 5434. Required `DATABASE_URL`, `REDIS_URL`,
`QDRANT_URL`, and a synthetic test-only `JWT_SECRET` were also supplied.

The earlier run with only the milestone database variables failed eight Settings
constructions: 158 passed / 8 failed. Supplying the required application test
configuration resolved those failures without editing frozen M6 code or tests.

Warnings: one existing AnyIO deprecation and four unawaited AsyncMock warnings in
M6 vector-adapter tests. These are disclosed, not suppressed or treated as proof
that vector interactions are fully verified. No live model calls were made.

## Remaining blockers

This checkpoint does not close the independent rejection:

- Complete M8-03/07/08/10/11 assertions, including the full HTTP tenant/ownership/
  forged-header matrix and measured budget/cycle enforcement.
- Integrate actual M6 evidence and validated explanations; the conservative
  fallback currently limits conversational functionality intentionally.
- Fix the evidence runner's failure handling, environment setup and exact-node
  M8-01–12 mapping. Do not reuse its unconditional PASS claims.
- Commit reviewed implementation, then separately generate and commit evidence,
  recording implementation SHA, migration head and verified final hashes.
- Obtain fresh independent sign-off. Passing tests alone do not certify M8.

No frozen M1–M7 files were edited by this remediation slice. Pre-existing worktree
changes were preserved. No new commits, evidence generation, staging, deployment,
or milestone unlock occurred. The rejected evidence package remains unchanged.
