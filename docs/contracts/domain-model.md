# M2 Domain Model

Version: 0.2 design draft, 2026-09-12. Initial offer, dream-company and compensation
decisions are [confirmed](m2-decisions.md). These are domain assumptions, not active
institutional policy. See [ERD](../architecture/domain-erd.md) and
[verification plan](../testing/m2-plan.md). M2 migrations are not applied yet.

All private entities are institution-scoped. UUID identifiers do not grant access.
Users map to institution, role, and (for students) a student identity.

Students have versioned academic facts, normalized semester records, backlogs,
skills and certifications with provenance. Missing marks are not zero.
Company → role → placement opportunity → immutable published requirement version.
Criteria record explicit Required/Not Applicable/Optional/Unknown states.

Offer events preserve received, accepted, rejected, withdrawn and expired history.
Policy chooses the qualifying state and selection strategy; events are not overwritten.
Dream declarations record company, student, source, timestamps and approval history.

Policies have immutable version definitions, typed rules, effective intervals,
approval and source locators. Documents retain original file, hash and version.
Eligibility checks reference immutable input snapshots and criterion/evidence rows.
Administrative overrides preserve and refer to the original decision.

Constraints will enforce scoped uniqueness, foreign keys, value ranges, version
uniqueness and non-overlapping active policy scope. Use Decimal/NUMERIC for marks
and packages, UTC-aware timestamps, and stable IDs for equal-valued selection ties.
Full table migrations and database invariant tests belong to M2.

## Ownership, vocabulary and common fields

Academic years are institution-defined cycles with start/end dates. A user is a
login identity; a student is a persistent institutional record. A company is an
employer; a role is a job; a drive is a recruitment event; an opportunity joins a
role and drive with its own requirement/package history. Receipt and acceptance
of an offer are distinct events. A dream declaration is a preference, not an
automatic exception. An evaluation is a decision plus immutable input/evidence.

All private rows have institution_id. Parents expose unique `(institution_id, id)`
keys, and children use composite foreign keys to prevent cross-tenant links. UUIDs
are not authorization. Repository queries always include authenticated tenant scope.
Companies are institution-scoped initially; no implicit global shared catalog.

Stable entities use UUIDs; revisions have unique parent/revision numbers. Effective
and recorded timestamps are separate, timezone-aware UTC values. Effective intervals
are half-open `[from, until)`. Material revisions/events preserve actor, source type,
verification state, request ID, import idempotency key, recording/effective times
and correction reason. Current pointers are projections over immutable history.

## Identity and academics

| Tables | Key relationships / values | Principal invariants |
| --- | --- | --- |
| institutions, academic_years | tenant identity; scoped cycle code and dates | Unique code; cycle start < end |
| users, roles, user_roles | scoped authentication identities and role assignments | Unique scoped login and assignment |
| students, student_revisions | roll/user link; versioned name, department, degree, graduation year | Scoped roll unique; at most one student per linked user |
| departments, degrees | scoped reference codes | Unique scoped code |
| grading_scales | immutable named minimum/maximum | min < max |
| student_academic_records | student/revision, SSLC/HSC/diploma/CGPA values, states, scales and provenance | Unique revision; known percentages 0–100 |
| student_semester_records | academic revision, semester, SGPA, scale and state | Unique revision/semester; positive semester |
| student_backlogs, student_backlog_events | obligation identity; OPENED/CLEARED/CORRECTED events | Ordered append-only event history |
| student_skills, student_certifications | versioned student values and verification/source | Self-declared distinct from verified |

Academic states are KNOWN, UNKNOWN and NOT_APPLICABLE. KNOWN requires a numeric
value; others require NULL. Zero is not missing. Presence is separate from verification.
No implicit HSC/diploma substitution or conversion to a ten-point grading scale.
Scale-bound validation that references another row needs a transaction/trigger;
an ordinary CHECK cannot query another table. Source precision must be retained.

Active backlog means an outstanding obligation at the snapshot instant. Historical
backlog counting (courses versus failed attempts) remains an explicit policy metric.
Imported aggregates preserve metric/as-of/source rather than fabricated course rows.

## Recruitment and requirements

| Tables | Key relationships / values | Principal invariants |
| --- | --- | --- |
| companies, company_revisions | stable employer and versioned details | Scoped code and parent/revision unique |
| company_roles | company, role code/title | Unique company/role code |
| placement_drives | company, academic year, original announcement, schedule, status | Original cutoff cannot be reset by rescheduling |
| placement_opportunities | drive, role, deadline, status | Drive and role share company and institution |
| company_requirements | stable set identity per opportunity | One set per opportunity |
| company_requirement_versions | parent/version, package terms, typed definitions, hash and publisher | Published definition immutable |
| requirement_activations | version, applicability scope, effective interval | Same-scope active intervals do not overlap |
| requirement_criteria | version, criterion code, applicability, operator, typed operand | Unique criterion/version; operand type validation |
| requirement_set_members | criterion, typed member or department/degree FK | Scoped members, no duplicates |

Applicability is REQUIRED, OPTIONAL, NOT_APPLICABLE or UNKNOWN. Missing threshold
does not mean unrestricted. Publication validates explicit expected criterion coverage.
Optional criteria cannot silently become eligibility blockers. Comparisons support
>, >=, <, <=, =, !=, IN, NOT_IN and BETWEEN. Complex expression JSON must be bounded
and schema-versioned, never executable SQL/Python or raw source-document prose.
Definition corrections create new versions. Activation interval changes are audited
separately from immutable package, operands and source bindings.

## Offers and compensation

| Tables | Key relationships / values | Principal invariants |
| --- | --- | --- |
| compensation_terms | original text, currency, period, basis, exact/range shape, amounts, comparison state/reason, derived annual INR and provenance | Nonnegative finite amounts; min <= max; explicit shape/state checks |
| student_offers | student, company, role, optional opportunity, academic year/context | Stable scoped identity, preserve external offers |
| student_offer_events | offer/sequence, event, effective/recorded time, terms, actor/source | Unique sequence/import key; append-only |

Immutable compensation terms serve both offers and requirement versions. Proposed
physical money type is NUMERIC(18,4). Comparable annual INR is present only for
verified exact annual total CTC in INR or a later explicitly authorized conversion.
Preserve unresolved source terms; never choose endpoints, annualize or convert silently.
Display INR 500000 as 5.00 LPA without changing authoritative precision.

Offer events include RECEIVED, ACCEPTED, REJECTED, REVOKED, WITHDRAWN, EXPIRED,
TERMS_REVISED and CORRECTED. Services validate transitions transactionally. Multiple
accepted offers remain storable; no uniqueness constraint may discard truthful history.
Choose the highest valid accepted offer in context under the confirmed baseline,
recording selected ID and rationale. Unknown context/terms cannot be silently ignored.
Revised terms and any renewed acceptance are recorded explicitly.

## Dream-company history and locks

`student_dream_companies` records student/company/year identity;
`dream_declaration_events` records declaration/approval/rejection/supersession and
policy references. `dream_drive_locks` binds the declaration revision to the
original announcement and applicable rule version.

Initial approved count is one per student/year. Declaration and approval must occur
strictly before announcement; student changes are prohibited afterward. Serialize
approval/change in the student/year scope to prevent concurrent limit bypass.
Count/cutoff are versioned rule parameters rather than a single permanent company
column on students. History and announced-drive locks survive later policy changes.
Queries/AI cannot mutate them. Equal-package permission requires active policy and
never bypasses unrelated requirements.

## Policy definitions and source provenance

| Tables | Key relationships / values | Principal invariants |
| --- | --- | --- |
| policies, policy_versions | stable identity; version, year, scope, definition schema/hash | Scoped version unique; active definition immutable |
| policy_lifecycle_events | version, transition, actor, reason, timestamp | Valid sequence; approval precedes activation |
| policy_activations | version, institution/year/scope, effective interval | No overlap in identical applicability scope |
| policy_rules | version, rule code, typed definition | Unique rule/version; approved schemas |
| policy_documents | immutable storage key/original, media type, hash, source version, uploader, status | Preserve originals; authorized storage access |
| policy_source_locators | document, page/section/offsets, source hash | Positive page or usable text locator |
| rule_source_links, requirement_source_links | rule/criterion to source locator | Scoped many-to-many provenance |

Lifecycle is DRAFT → PROCESSING → REVIEW → APPROVED → ACTIVE → ARCHIVED.
Activation is atomic and authorized. M2 assumptions do not seed active policies.
Use PostgreSQL constraints and transaction locking to prevent same-scope overlap.
Different simultaneously applicable scopes need explicit composition; no latest-wins
fallback. Unresolved/imported conflicts lead to UNKNOWN in M5.

## Evaluations, audit and replay storage

| Tables | Key relationships / values | Principal invariants |
| --- | --- | --- |
| eligibility_checks | student, opportunity, actor/request, decision, time, engine version | Three primary states; completed records immutable |
| eligibility_snapshots | check, schema version, full canonical payload/hash | One snapshot per completed check |
| eligibility_criteria_results | check, rule/ordinal, compared values/operator, outcome/reason | Four criterion states; stable ordering |
| eligibility_evidence | check/criterion, source locator, immutable excerpt/hash | Evaluated source versions preserved |
| administrative_overrides | check, actor, reason, evidence, scope, disposition/time | Original decision remains intact |
| audit_logs | tenant, actor, action, resource/revision references, request/time | Append-only, access-scoped |

Decisions are ELIGIBLE, NOT_ELIGIBLE, UNKNOWN; criteria are PASS, FAIL, UNKNOWN,
NOT_APPLICABLE. Review-needed is metadata. Capture the complete student/offer/dream/
requirement/policy input from a consistent repeatable-read transaction and save it
atomically with outcomes/evidence. Failed persistence cannot return success.

Snapshots use schema-versioned canonical JSON with decimal strings, UTC timestamps,
stable ordering and hashes. Store actual definitions/values, not just hashes or IDs
pointing at mutable current rows. Backdated corrections create new evaluations.
Replay uses saved facts and a retained compatible engine version, not today's data.
Unsupported engine versions yield explicit failure. Snapshot access is privacy-scoped.

Agent tables remain in the roadmap catalog; detailed session/message/tool-call
schemas follow the agent contract. Any deferral must be stated in M2 coverage rather
than claiming all catalog tables implemented.

## Repository, index and migration boundaries

Repositories handle scoped persistence/read models; application unit-of-work owns
transactions. ORM models do not implement eligibility or call AI/vector providers.
Indexes target scoped identity, parent/revision, offer/student/context, event/time,
dream/student/year, opportunity/drive/status, applicability and evaluation/student/time.
Add JSON indexes only for known queries. Reference seeds contain no credentials,
real students or fake active policy.

Validate models/migrations/constraints against empty PostgreSQL and synthetic fixtures,
including tenant boundaries, concurrency, idempotency, upgrade/downgrade/upgrade and
backup/restore. Use isolated test volumes; preserve the running M1 stack.
