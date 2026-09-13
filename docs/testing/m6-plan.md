# M6 design and verification gate

Date: 2026-09-13. Status: DESIGN_APPROVED; implementation in progress.
Five independent-review clarifications incorporated in [contract v0.2](../contracts/rag-contract.md).
Certified baseline: [M5 commit and caveat](../project-status/m5.md).

## Traceable acceptance cases

| ID | Test requirement | Required evidence |
| --- | --- | --- |
| M6-01 | PDF/MD/TXT upload and preservation | Stored original bytes hash equals submitted bytes; provenance resolves |
| M6-02 | Legacy metadata-only source | Missing object is SOURCE_UNAVAILABLE, never empty successful content |
| M6-03 | Source binding | Only reviewed binding/version is retrievable; cannot activate a rule |
| M6-04 | Parsing/locators | Known page, heading and offset fixtures resolve exact preserved excerpts |
| M6-05 | Unsupported/scanned/encrypted content | Review/failure with stable code; no fabricated text or pages |
| M6-06 | Malformed/oversized files | MIME/extension/path/size/extraction caps, parser timeout and network isolation |
| M6-07 | Chunking | Deterministic IDs/hashes, bounded size, no untraceable page crossing |
| M6-08 | Embedding contract | Wrong dimension/count, NaN/Infinity and provider failures rejected |
| M6-09 | Idempotency/concurrency | Same input/config has one logical run; duplicate workers cannot publish duplicates |
| M6-10 | Partial index | Crash after partial upsert cannot publish it; restart/retry completes manifest |
| M6-11 | Current policy | Exact institution/year/scope/ACTIVE interval; expired/future/wrong scopes excluded |
| M6-12 | Historical evidence | Authorized decision pins original policy version despite newer ACTIVE version |
| M6-13 | No/ambiguous policy | Explicit failure, no historical fallback; ambiguity seam has real assertions |
| M6-14 | Tenant/role boundary | Foreign IDs, source URLs and forged Qdrant payloads cannot return content |
| M6-15 | Stale index | Revoked binding/archive/context change filtered by authoritative recheck |
| M6-16 | Citation integrity | Tampered source/chunk hash, offset/page and nonexistent chunk rejected |
| M6-17 | Outage/abstention | Embedding/Qdrant unavailable, index unready and empty match are distinct |
| M6-18 | Prompt injection | Embedded commands remain inert source data; no tool/SQL/policy mutation |
| M6-19 | Frozen decisions | Retrieve/fail/cancel and reindex leave saved M5 result/snapshot/key unchanged |
| M6-20 | Recovery | Restore bytes + metadata; rebuild index; identical valid locators/manifests |
| M6-21 | Regression | Run M1–M5 suite unmodified and new M6 tests; report assertionless-test caveat |

## Fixed retrieval benchmark (proposed gate)

Before tuning, version and hash a synthetic corpus and labels: at least two tenants,
two academic years, current/historical/future/expired policies, scopes, duplicate
phrases, conflicting-looking documents, tables, and prompt-injection passages.
Include at least 40 answerable questions and 20 unanswerable/security/context cases.
Every answerable question has gold document/version/locator IDs and relevance labels;
unanswerable cases declare the expected absence/error condition.

Separate development questions from held-out evaluation questions. Freeze labels
before the final run; report parser/chunker/model/dimensions, generation, top_k,
corpus/label hashes, seed where applicable and exact code commit. Mock embeddings
prove interface/error behavior only, not semantic retrieval quality.

Proposed thresholds for review:

- Zero cross-tenant or unauthorized-source disclosures.
- 100% correct policy/version scope among returned evidence.
- 100% returned citations resolve to exact stored chunks/locators/hashes.
- Recall@5 >= 0.90 across answerable questions (relevant gold chunks retrieved /
  relevant gold chunks), with per-question failures disclosed.
- 100% specified abstention/error cases handled without unsupported evidence.
- No changed M5 decision, snapshot or evaluation key caused by an M6 operation.

Citation integrity and retrieval relevance are independently scored gates. A valid
but irrelevant chunk can pass provenance validation but contributes zero relevant
hits to Recall@5. Neither metric substitutes for the other. Binding tests must
exercise forbidden reapproval and immutable event history; publication tests must
exercise wrong counts/manifests/hashes/dimensions and exact published-ID filtering.

Report Precision@5 and latency distributions too; do not hide retrieval failures
inside the aggregate. Initial latency target is retrieval p95 < 3s on a documented
warm-index workload. Dataset size, concurrency, token volume, machine/resources,
provider latency and cost must accompany any performance statement.

## Evidence package

The eventual M6 evidence directory must contain pinned commit/diff scope, migration
head, reproducible commands and outputs, collected/asserted test counts, benchmark
fixtures/labels/hashes, security/negative results, recovery comparison and dependency
versions. Preserve original M5 evidence unchanged; reference its no-op ambiguity case
without claiming that it proves defensive handling.

Implementation evidence is recorded separately in the M6 status document. No M6
certification is implied by contract approval or by passing isolated unit tests.
