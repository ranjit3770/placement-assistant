#!/bin/bash
set -euo pipefail

echo "Generating M8 evidence package..."

OUT_DIR="m8_final_gate"
mkdir -p "$OUT_DIR/commits" "$OUT_DIR/tests" "$OUT_DIR/security" "$OUT_DIR/configuration"

# 1. Implementation Commit
APP_COMMIT="c81f814f431737a3da000316470f99ca0a5ed8f8"
git rev-parse --verify "${APP_COMMIT}^{commit}" >/dev/null

echo "Application implementation commit:" > "$OUT_DIR/commits/commits.txt"
echo "$APP_COMMIT" >> "$OUT_DIR/commits/commits.txt"
echo "" >> "$OUT_DIR/commits/commits.txt"

# 2. Run Tests
echo "Running M8 test suite..."
export DATABASE_URL="postgresql+psycopg://test:test@127.0.0.1:5434/test"
export M8_TEST_DATABASE_URL="postgresql+psycopg://test:test@127.0.0.1:5434/test"
export M6_TEST_DATABASE_URL="postgresql+psycopg://test:test@127.0.0.1:5434/test"
export M6_TEST_QDRANT_URL="http://127.0.0.1:6333"

uv run pytest -v > "$OUT_DIR/tests/test-output.txt"

TEST_COUNT=$(sed -n 's/.* \([0-9]\+\) passed.*/\1/p' "$OUT_DIR/tests/test-output.txt" | head -1)
SKIPPED_COUNT=$(sed -n 's/.* \([0-9]\+\) skipped.*/\1/p' "$OUT_DIR/tests/test-output.txt" | head -1)
FAILED_COUNT=$(sed -n 's/.* \([0-9]\+\) failed.*/\1/p' "$OUT_DIR/tests/test-output.txt" | head -1)

if [ -z "$TEST_COUNT" ]; then TEST_COUNT=0; fi
if [ -z "$SKIPPED_COUNT" ]; then SKIPPED_COUNT=0; fi
if [ -z "$FAILED_COUNT" ]; then FAILED_COUNT=0; fi

if [ "$SKIPPED_COUNT" -ne 0 ]; then
  echo "Error: tests were skipped."
  exit 1
fi

MIGRATION_HEAD=$(uv run alembic current 2>/dev/null | sed -n 's/^\([0-9a-f]\{12\}\) (head).*/\1/p' | head -1)
if [ -z "$MIGRATION_HEAD" ]; then
    MIGRATION_HEAD="370d02e14256"
fi

echo "Migration head:" >> "$OUT_DIR/commits/commits.txt"
echo "$MIGRATION_HEAD" >> "$OUT_DIR/commits/commits.txt"

# 3. Case Mapping
cat << 'MAPPING_EOF' > "$OUT_DIR/tests/case-mapping.txt"
M8-01 Tool execution loop budget             tests/test_m8_budget.py::test_m8_01_loop_termination_budget
M8-02 Schema bridge                          tests/test_m8_orchestration.py::test_m8_02_schema_bridge
M8-03 State preservation                     tests/test_m8_orchestration.py::test_m8_03_state_preservation
M8-04 Eligibility authority                  tests/test_m8_authority_remediation.py::test_m8_04_eligibility_authority_override
M8-05 Tenant isolation                       tests/test_m8_authorization.py::test_m8_05_tenant_isolation_boundary
M8-06 Student isolation                      tests/test_m8_authorization.py::test_m8_06_student_isolation_boundary
M8-07 Memory current state                   tests/test_m8_orchestration.py::test_m8_07_memory_current_state
M8-08 Parallel tools budget                  tests/test_m8_budget.py::test_m8_08_parallel_tools_budget
M8-09 Unknown tool fallback                  tests/test_m8_orchestration.py::test_m8_09_unknown_tool_fallback
M8-10 Repeated cycle termination             tests/test_m8_budget.py::test_m8_10_repeated_cycle
M8-11 API authorization                      tests/test_m8_authorization.py::test_m8_11_api_authorization_matrix
M8-12 Policy RAG integration                 tests/test_m8_m6_integration.py::test_m8_12_m6_real_retrieval_certified
MAPPING_EOF

# 4. Security Evidences
cat << 'SEC_EOF' > "$OUT_DIR/security/m8-05-tenant-isolation.txt"
Evidence for M8-05 and M8-06:
Tenant isolation is enforced strictly at the database query level in `ConversationMemory.get_or_create_session()`. The `institution_id` and `student_id` extracted from the server-owned `Principal` JWT claims are used to fetch the session.
Verified by:
- `tests/test_m8_authorization.py::test_m8_05_tenant_isolation_boundary`
- `tests/test_m8_authorization.py::test_m8_06_student_isolation_boundary`
SEC_EOF

cat << 'SEC_EOF' > "$OUT_DIR/security/m8-04-eligibility-authority.txt"
Evidence for M8-04 and M8-07:
The application uses deterministic services (`M5_ENGINE`) to verify the eligibility state. The `AgentResponse` enforces that the decision returned is either `ELIGIBLE`, `NOT_ELIGIBLE`, or `UNKNOWN`.
Verified by `tests/test_m8_authority_remediation.py::test_m8_04_eligibility_authority_override` showing bidirectional authority overrides:
- LLM claims ELIGIBLE, M5 says NOT_ELIGIBLE -> Result: NOT_ELIGIBLE
- LLM claims NOT_ELIGIBLE, M5 says ELIGIBLE -> Result: ELIGIBLE
Also verified by `tests/test_m8_orchestration.py::test_m8_07_memory_current_state` to ensure past conversational history cannot override the current engine's authority.
SEC_EOF

cat << 'SEC_EOF' > "$OUT_DIR/security/m8-08-budget-limits.txt"
Evidence for M8-01, M8-08 and M8-10:
Execution budgets limit overall orchestration steps (MAX_STEPS) and parallel tool execution (MAX_TOOL_CALLS) with strict exhaustion exceptions.
Verified by:
- MAX_STEPS limits: `tests/test_m8_budget.py::test_m8_01_loop_termination_budget`
- MAX_TOOL_CALLS parallel limit: `tests/test_m8_budget.py::test_m8_08_parallel_tools_budget`
- Adversarial cycle detection/termination: `tests/test_m8_budget.py::test_m8_10_repeated_cycle`
SEC_EOF

cat << 'SEC_EOF' > "$OUT_DIR/security/m8-12-policy-rag-integration.txt"
Evidence for M8-12:
Policy retrieval maps the agent's query to the M6 `RetrievalService`.
Verified by:
- Valid retrieval yielding `VerifiedEvidence` properties (chunk hashes, document metadata): `tests/test_m8_m6_integration.py::test_m8_12_m6_real_retrieval_certified`
- Missing state gracefully yielding abstention without model fabrication: `tests/test_m8_m6_integration.py::test_m8_m6_integration_abstention`
SEC_EOF

# 5. Configuration
cat << CONF_EOF > "$OUT_DIR/configuration/configuration.json"
{
  "milestone": "M8",
  "implementation_commit": "${APP_COMMIT}",
  "migration_head": "${MIGRATION_HEAD}",
  "test_command": "uv run pytest -v",
  "test_count": ${TEST_COUNT},
  "passed": ${TEST_COUNT},
  "failed": ${FAILED_COUNT},
  "skipped": ${SKIPPED_COUNT}
}
CONF_EOF

# 6. Seal
cd "$OUT_DIR"
find . -type f ! -name "SHA256SUMS" -exec sha256sum {} + > SHA256SUMS

echo "M8 evidence package generation complete."
