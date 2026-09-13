# M4 Final Gate Evidence

## Verification Matrix

| Area | Evidence | Status |
|------|----------|--------|
| **Document Metadata** | API correctly simulates upload by calculating `content_hash` from payload and returning `storage_key`. | 🟢 PASS |
| **Policy Namespace** | `Policy` and `PolicyVersion` correctly separated. | 🟢 PASS |
| **State Machine** | `transition_status` enforces `DRAFT -> PROCESSING -> REVIEW -> APPROVED -> ACTIVE -> ARCHIVED` | 🟢 PASS |
| **Immutability** | `add_policy_rule` blocks mutations when `status in ("APPROVED", "ACTIVE", "ARCHIVED", "REVIEW")` | 🟢 PASS |
| **Authorization** | `approve_policy` and `activate_policy` enforce `COORDINATOR` or `ADMIN` roles | 🟢 PASS |
| **Provenance** | Every event creates a `PolicyEvent` capturing target `status`, `actor_id` (FK), and `reason` containing the `FROM -> TO` transition. | 🟢 PASS |
| **Activation Overlap** | Handled by `ex_policy_activation_overlap` DB constraint, returns 409 | 🟢 PASS |
| **Atomicity** | `activate_policy` executed in same transaction | 🟢 PASS |
| **Archive Reconcile** | Archiving a policy closes its active `PolicyActivation` by setting `ends_at` | 🟢 PASS |
| **Concurrency** | Tested by `test_concurrent_policy_activation` and `test_concurrent_api_activation` with actual overlapping API race conditions | 🟢 PASS |

## Test Evidence
All tests run successfully. See `m4_final_gate/tests.txt` for the API logs showing endpoints returning `201`, `200`, `409` (Overlap/Conflict), `400` (Invalid Transition), and `403` (Unauthorized).
