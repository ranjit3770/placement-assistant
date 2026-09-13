# M6 contract — Policy RAG and verified evidence

Version: 0.2, 2026-09-13. Status: DESIGN APPROVED WITH CONDITIONS INCORPORATED.
Independent review baseline: `3a30b94c36f8eaa4ad28f0b0674f1d4149330592`.
Implementation is unlocked; this is not implementation certification.
Baseline: [certified M5](../project-status/m5.md), SRS §§17–23, 47–49, 65–68,
74–76, 88 and roadmap M6. Proposed defaults below are reviewable M6 choices,
not already implemented functionality or activated institutional policy.

## 1. Scope and boundary

M6 preserves PDF/Markdown/TXT originals, parses/chunks them, generates embeddings,
indexes Qdrant and returns tenant-authorized policy excerpts with verifiable
citations. PostgreSQL remains the authority for source identity and policy binding.
Qdrant is a replaceable retrieval adapter, not an executable policy store.

M1–M5 are frozen. Do not modify evaluator algebra, snapshots, decision rows,
idempotency keys, policy/requirement authority or replay to add retrieval. An M6
request cannot write an EligibilityDecision. No agents, autonomous actions, rule
extraction/activation or generated decision-making are introduced in M6.
Generated policy answers/validated AI explanations are a subsequent R2 increment;
this contract returns excerpts and structured evidence. OpenAI embeddings are a
provider adapter configured independently from domain logic.

## 2. Existing integration surfaces and dependency

Read existing Document, SourceLocator, PolicyVersion, PolicyActivation and
EligibilityDecision through tenant-scoped repositories/adapters. Preserve all
existing public routes and migration revisions.

Concrete dependency: `PolicyService.create_document` hashes a supplied string and
creates a simulated storage key; it does not store the original bytes. M6 must
not assume those keys resolve. Add a new file upload/storage service and ingestion
route. Existing metadata-only records remain SOURCE_UNAVAILABLE until an authorized
matching-byte import succeeds; do not fabricate content or overwrite original hashes.

Existing rule/source links are insufficient to assume all document text was approved
for retrieval. Add an explicit approved source binding from document to policy version.
Binding approval permits citation, not rule creation or activation. It records the
reviewer, time, source hash, policy version and any historical source verification.
Attaching late evidence to a historical decision must be labeled as later retrieval,
not as evidence captured in the original certified decision.

Binding revisions are immutable identities with append-only lifecycle events.
The only transitions are `PROPOSED -> APPROVED -> REVOKED`. Approval records the
authorized reviewer, timestamp and exact source hash. Revocation does not erase
approval provenance. `REVOKED -> APPROVED` is forbidden: reapproval requires a new
proposed revision and fresh review. Concurrent transitions must serialize on the
binding identity; retries cannot append conflicting events.

## 3. Additive persistence model

Proposed new tables, using the existing tenant/provenance conventions:

| Entity | Purpose / invariants |
| --- | --- |
| rag_source_objects | Document ID, private object key, byte length, verified hash; preserved original bytes |
| rag_policy_sources | Document/version binding and approval/revocation events; scoped FKs; cannot mutate rule definitions |
| rag_ingestion_runs | Document/binding, parser/chunker/embedding versions, schema version, idempotency key, status/error, attempt/lease |
| rag_chunks | Run/document, ordinal, canonical text, page/section/offsets, source/artifact/chunk hashes |
| rag_index_generations | Embedding space, expected point manifest/count, completed state and published generation |
| rag_jobs | Durable queued work, lease and retry timestamps; recoverable without Redis |
| rag_retrieval_events | Authorized context, version/generation, selected chunk IDs, bounded timings/status; no unnecessary raw query/PII |

References are composite institution/ID keys. Immutable chunk text and locators
must correspond to a hashed normalized artifact. A new parser/chunker/embedding
configuration creates a new generation; never silently changes historical evidence.
Database writes and job creation are transactional. Object and vector writes are
external operations with reconciliation; no claim of a distributed SQL transaction.

Hash definitions are distinct and mandatory:

- `source_hash = SHA256(original uploaded bytes) = Document.content_hash`.
- `normalized_artifact_hash = SHA256(exact normalized UTF-8 extraction artifact)`.
- `chunk_hash = SHA256(canonical chunk representation)`.

Canonical chunk representation uses UTF-8 JSON with sorted keys, no insignificant
whitespace, no ASCII escaping, and no NaN. It includes schema version, exact text,
source/artifact hashes, ordinal and locator. Locator offsets are Unicode code-point
indices into the normalized artifact. Normalization never changes the M4 hash.

## 4. Ingestion contract

```text
Authorized upload → verify bytes/hash → preserve original → durable job
→ parse → normalize with source locators → chunk → embed → Qdrant upsert
→ verify complete manifest → publish generation in PostgreSQL
```

Proposed job states: QUEUED, RUNNING, READY, REVIEW_REQUIRED, FAILED, CANCELLED.
These are processing states, separate from policy lifecycle and eligibility states.
Store a stage/checkpoint, retry count and stable error code rather than exception text.

PDF extraction preserves 1-based page numbers; chunks cannot cross page boundaries
without an explicit multi-page locator. Markdown/TXT use Unicode code-point offsets
into an immutable normalized UTF-8 artifact and heading sections where available.
Never invent PDF page numbers for text files. Whitespace/Unicode normalization
must preserve a traceable locator into the saved artifact; keep original file hash too.

Scanned/no-extractable-text and encrypted/unsupported PDFs require review; OCR is
deferred. Parsing errors do not result in empty successful indexes. Tables should
retain readable context or be marked for review when parsing loses the relationships.

Proposed defaults: 10 MiB upload, 200 PDF pages, 2 million extracted characters,
800-token chunks with 100-token overlap within locator boundaries. Enforce actual
embedding provider input limits; tokenizer/model configuration is versioned. These
defaults are configuration, not hard-coded institutional rules.

Idempotency key includes institution, document/source hash, policy binding and all
pipeline/embedding versions. Duplicate same-key requests return the same run.
Chunk/point IDs derive deterministically from that manifest and ordinal. Retry can
upsert the same points safely. Partially indexed generations are never visible.
Old valid generations remain readable until a new complete one is published.

Reader-atomic publication requires all of: expected chunk count equals indexed
count, expected point manifest equals actual point manifest (including hashes),
source/artifact/chunk hashes validate, and every vector has the configured finite
dimensions. Only then may a transaction mark the generation `PUBLISHED` and change
the binding's `published_generation_id`. Readers select and filter that exact ID,
never the newest run or a partially written generation. Cancellation/revocation
must be rechecked in the publication transaction. Qdrant payload is not authority;
independent PostgreSQL approval, nonrevocation and applicability checks are a
certification blocker, even when the vector query included all required filters.

Use bounded exponential backoff with jitter, at most three transient retries;
validation/authorization failures are not retried. Proposed limits: parser 60s,
embedding request 30s, vector request 5s; worker lease with heartbeat and capped
total job duration (initially 15 minutes). Expired leases are recoverable. Request
cancellation must not lose already committed jobs; cancellation state prevents publish.

## 5. Retrieval context and authorization

All context comes from authenticated identity and authorized resource lookups.
Clients cannot provide institution IDs, arbitrary Qdrant filters/collections or
storage paths. Staff writes require explicit COORDINATOR/ADMIN authorization;
student requests are read-only and limited to permitted published evidence.

Current-opportunity queries derive year from the persisted drive and use the
certified current scope (`ALL`) and half-open activation interval. Do not invent
department precedence or fallback to a more convenient historical policy. An M6
read-only resolver must match this predicate, with compatibility tests against
the certified behavior; it must not refactor the frozen M5 private method.

Historical/decision queries pin an authorized decision's policy version and retain
that version even if a newer policy is ACTIVE. Explicit historical staff queries
require year/version authorization and are clearly labeled HISTORICAL. Conversation
history or user prose cannot choose a different policy for a current decision.

Selection filters are mandatory AND predicates: institution, document/source approval,
policy version, academic year, scope and published generation/embedding space.
Apply them in the Qdrant query, then independently verify each candidate against
PostgreSQL before returning content. A stale/forged payload cannot bypass access
checks, source revocation or version matching. Recheck binding/policy applicability
before response; if it changed during retrieval, retry once or return CONTEXT_CHANGED.

No source binding/version match means no evidence, never a fallback to another
institution/year/policy. Resolve missing or ambiguous context explicitly; do not
treat higher similarity as greater policy authority.

## 6. Embedding and vector interfaces

Interfaces: DocumentStore, DocumentParser, Normalizer, Chunker, EmbeddingProvider,
VectorIndex and EvidenceRepository. Each has typed input/output, bounded operations
and stable failure categories. Keep SDK types out of service/domain contracts.

`EmbeddingProvider` is provider-agnostic: local, OpenAI and future implementations
use the same interface. Domain logic cannot branch on provider identity. Every
generation persists provider, model, dimensions, tokenizer, distance metric and
pipeline version; the complete configuration defines its embedding-space identity.

Embedding configuration includes provider, model identifier, dimensions, tokenizer,
pipeline version and distance metric. Do not mix incompatible spaces in one query.
Validate vector count, dimensions and finite values before indexing. Set collection
names server-side; never accept them from callers. Quotas and chunk/page caps bound cost.
Production embedding selection is pinned before benchmark execution; changing it
requires a new generation and reevaluation. No live provider call occurs at design time.

Payload includes institution_id, document_id, policy_id, policy_version_id/version,
academic_year_id, scope, binding_id, run/generation ID, chunk ID/ordinal, page/section/
offsets, source hash, normalized-artifact hash, chunk hash and embedding-space ID.
Cached retrieval keys include tenant, authorization scope, exact policy version,
binding revision and generation. Disable caching initially until invalidation is tested.

## 7. Proposed API and response contract

| Route | Operation |
| --- | --- |
| POST /api/v1/rag/documents | Authorized multipart upload; preserve bytes and source metadata |
| POST /api/v1/rag/source-bindings | Staff proposes document/policy-version association |
| POST /api/v1/rag/source-bindings/{id}/approve | Authorized source approval with audit; no policy transition |
| POST /api/v1/rag/source-bindings/{id}/revoke | Revokes retrievability; preserves audit/history |
| POST /api/v1/rag/documents/{id}/ingestions | Queue idempotent processing of an authorized binding; 202 |
| GET /api/v1/rag/ingestions/{id} | Scoped stage/status/error metadata |
| POST /api/v1/rag/search | Structured excerpt retrieval for authorized opportunity or historical context |
| GET /api/v1/rag/evidence/{chunk_id} | Verify and return source-backed excerpt/locator |

Search accepts a bounded query (proposed 2,000 characters), one context mode and
top_k (default 5, maximum 10). Modes are CURRENT_OPPORTUNITY, DECISION_EVIDENCE or
explicit HISTORICAL. Incompatible/missing context fields are validation errors.
It returns retrieval_status, context_mode, exact policy/version, retrieved_at,
request_id, embedding/generation IDs and evidence[]. No eligibility result field.

Each evidence entry includes document/version/hash, binding/chunk ID, exact excerpt,
locator/artifact hash, policy version, and authenticated source link. M6 citations
are constructed from stored metadata, never LLM-created filenames or page numbers.
Relevance scores are not correctness probabilities. Unknown source text or broken
locator/hash fails validation; do not return a plausible-looking citation.

Empty authorized search returns 200 with NO_MATCH and empty evidence. Missing source,
missing policy, ambiguity, unready index and provider outage have distinct stable
codes (SOURCE_UNAVAILABLE, NO_ACTIVE_POLICY, POLICY_AMBIGUITY, INDEX_NOT_READY,
DEPENDENCY_UNAVAILABLE); transport semantics are documented in OpenAPI. Unauthenticated
requests receive 401; unknown/cross-tenant resources share 404; forbidden operations
receive 403. Rate/quota limits receive 429. No provider exception details leak.

An existing M5 decision remains unchanged on every retrieval failure. Display
“policy evidence unavailable” separately from its stored result. An evidence-only
question with insufficient support yields no supported answer; M6 never persists
a fabricated UNKNOWN decision as a substitute for retrieval status.

## 8. Security and operations

Allow PDF/MD/TXT only; check extension and content/media agreement, size and extraction
limits. Generate private object keys; ignore caller paths; no arbitrary URL fetching.
Disable parser network access/active PDF content, bound CPU/memory and reject malformed
inputs. Local development uses a private mounted source volume behind DocumentStore;
production requires controlled durable storage, malware-scanning policy and backups.

No student profiles/offer histories are embedded. Only necessary approved policy
text is sent to the configured embedding provider. Treat document instructions as
untrusted data; no tools, SQL or rule activation can be invoked by source text.
Logs contain IDs, durations, stage/error codes and counts, not raw documents,
queries, provider secrets or presigned source URLs.

PostgreSQL, originals and manifests allow index reconstruction. Test backup/restore
of originals and metadata plus Qdrant reindex recovery. Retries/reconciliation clean
up unreachable partial generations without deleting pinned historical sources.
Retention/revocation must distinguish blocking future retrieval from deleting
evidence required for an authorized audit.

## 9. Implementation sequence and independent gate

1. Approve this contract, integration/dependency record and evaluation thresholds.
2. Add source storage, bindings, jobs and additive migrations; test tenant/security.
3. Add parser/locator/chunker tests before embedding adapters.
4. Add embedding/Qdrant adapters, versioned manifests and recovery/idempotency tests.
5. Add scoped retrieval/API and citation validation with no M5 decision mutation.
6. Run fixed benchmark, dependency-outage cases and full frozen M1–M5 regression.
7. Produce pinned evidence and request independent M6 review; do not self-certify.

Detailed acceptance matrix: [M6 verification plan](../testing/m6-plan.md).
