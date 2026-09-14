# AI Placement Assistant — Developer Onboarding

> **Purpose:** This document is the first thing a new developer should read before working on the AI Placement Assistant.

---

## 1. Welcome

Welcome to the **AI Placement Assistant**.

This project is an AI-assisted student placement intelligence platform.

The system helps answer questions such as:

> **"Can this student apply for this company/placement opportunity under the institution's current placement policies?"**

The system must produce a decision that is:

* deterministic where business rules are involved
* explainable
* traceable to source data
* tenant-isolated
* auditable
* reproducible
* safe against AI hallucination

### Most important principle

**AI explains. Deterministic business logic decides.**

The LLM must never invent or override an eligibility decision.

---

# 2. What Are We Building?

The platform combines:

```text
Student Data
     +
Company Requirements
     +
Institution Placement Policy
     ↓
Policy / Rule Processing
     ↓
Deterministic Eligibility Engine
     ↓
Eligibility Decision
     +
Evidence
     +
Explanation
```

Example:

```text
Student:
    CGPA = 8.2
    Backlogs = 0
    Previous accepted offer = ₹5 LPA

Company:
    Package = ₹6 LPA
    Minimum CGPA = 7.5
    Backlogs allowed = 0

Policy:
    Students cannot attend companies
    below or equal to their applicable
    previous accepted offer.

Result:
    ELIGIBLE
```

The AI agent may explain **why** the student is eligible.

It must not independently calculate or override the authoritative decision.

---

# 3. Technology Stack

The technology stack is intentionally fixed.

| Layer             | Technology              |
| ----------------- | ----------------------- |
| Frontend          | Next.js                 |
| Backend           | FastAPI                 |
| Database          | PostgreSQL              |
| Vector Database   | Qdrant                  |
| Cache / Events    | Redis                   |
| AI                | OpenAI API              |
| Deployment        | Docker / Docker Compose |
| Reverse Proxy     | Nginx                   |
| Backend Language  | Python                  |
| Frontend Language | TypeScript              |

Do not replace major components without an architectural decision.

---

# 4. Repository Structure

The repository broadly follows this structure:

```text
placement-assistant/
│
├── apps/
│   ├── web/                    # Next.js frontend
│   │
│   └── api/                    # FastAPI backend
│       ├── app/
│       │   ├── domain/
│       │   ├── application/
│       │   ├── infrastructure/
│       │   └── ...
│       │
│       ├── migrations/
│       └── tests/
│
├── docs/
│   ├── contracts/
│   ├── architecture/
│   ├── testing/
│   └── ONBOARDING.md
│
├── infrastructure/
│   ├── docker/
│   ├── scripts/
│   └── ...
│
├── .github/
│   └── workflows/
│
└── README.md
```

Before modifying code, understand where the change belongs.

---

# 5. The Most Important Documentation

Do not start by reading every source file.

Read the project contracts first.

Recommended order:

```text
1. docs/ONBOARDING.md
       ↓
2. README.md
       ↓
3. docs/contracts/domain-model.md
       ↓
4. docs/contracts/business-rules.md
       ↓
5. docs/contracts/policy-lifecycle.md
       ↓
6. docs/contracts/eligibility-contract.md
       ↓
7. docs/contracts/release-scope.md
       ↓
8. docs/architecture/
       ↓
9. docs/testing/
```

The contracts define **what the system is allowed to do**.

Code is expected to implement those contracts.

---

# 6. Authoritative vs Non-Authoritative Sources

This distinction is critical.

## Authoritative

These define system behavior:

```text
Domain contracts
Business rules
Policy lifecycle rules
Eligibility contract
Database constraints
Approved policy definitions
Validated student facts
Approved company requirements
```

## Non-authoritative

These may assist understanding but cannot override the contracts:

```text
LLM responses
RAG responses
Chat history
Prompt suggestions
AI-generated explanations
Developer assumptions
Temporary fixtures
```

If an AI response conflicts with a deterministic rule:

> **The deterministic rule wins.**

---

# 7. AI Agent Architecture

The project uses an AI agent, but the agent is controlled.

Conceptually:

```text
                 ┌──────────────────┐
                 │    AI Agent      │
                 │  Orchestrator    │
                 └────────┬─────────┘
                          │
             ┌────────────┼────────────┐
             ↓            ↓            ↓
        Student Tool   Policy Tool  Eligibility
                                      Tool
                                         │
                                         ↓
                              Deterministic Engine
                                         │
                                         ↓
                                  Authoritative Result
```

The agent can:

* understand the user's request
* identify required information
* call authorized tools
* retrieve policy evidence
* request an eligibility evaluation
* explain the result
* abstain when evidence is insufficient

The agent cannot:

* modify authoritative policy rules
* invent student facts
* override eligibility
* bypass authorization
* directly modify production data without an authorized workflow

---

# 8. Critical Business Rule: Previous Offer

One important M2 domain decision is:

> The applicable previous offer is the highest-value accepted offer that is not revoked, withdrawn, or expired.

Example:

```text
Offer A = ₹4 LPA → accepted
Offer B = ₹5 LPA → accepted
Offer C = ₹6 LPA → withdrawn

Applicable previous offer = ₹5 LPA
```

The withdrawn ₹6 LPA offer must not be used.

---

# 9. Critical Business Rule: Dream Company

The initial domain decision is:

> One approved dream company per student per academic year.

The declaration must satisfy the required lifecycle rules, including approval before the drive announcement.

Dream-company status is **not a universal bypass**.

Example:

```text
Company package = ₹5 LPA
Previous accepted offer = ₹5 LPA
Dream company = YES
```

This may be allowed only if the institutional policy explicitly permits the dream-company exception.

However:

```text
Minimum CGPA requirement = 8.5
Student CGPA = 7.2
```

Dream-company status does **not** automatically bypass the CGPA requirement.

---

# 10. Compensation Rule

The initial authoritative comparable compensation model is:

```text
Currency:
    INR

Period:
    Annual

Basis:
    Total CTC

Shape:
    EXACT

Value:
    Verified
```

Display:

```text
₹5 LPA
```

Internally:

```text
₹500000 annual total CTC
```

If compensation cannot be safely compared because of:

* ranges
* different currencies
* different compensation bases
* incomplete information
* unresolved conversion

the system must not guess.

The correct result may be:

```text
UNKNOWN
```

---

# 11. Eligibility Results

The eligibility engine uses explicit outcomes.

```text
ELIGIBLE
NOT_ELIGIBLE
UNKNOWN
```

### ELIGIBLE

All applicable requirements are satisfied and sufficient evidence exists.

### NOT_ELIGIBLE

At least one authoritative rule clearly fails.

### UNKNOWN

The system cannot safely determine eligibility.

Examples:

```text
Missing student CGPA
Missing company requirement
Unresolved compensation
Conflicting policy versions
Insufficient evidence
```

**UNKNOWN is a valid and important result.**

Never convert UNKNOWN into ELIGIBLE just to make the user experience look better.

---

# 12. Multi-Tenant Security

Every institution is a separate tenant.

Conceptually:

```text
Institution A
 ├── Students
 ├── Companies
 ├── Policies
 └── Evaluations

Institution B
 ├── Students
 ├── Companies
 ├── Policies
 └── Evaluations
```

Institution A must never be able to read Institution B's data.

Tenant isolation is a **security invariant**.

Repository code must therefore use an authenticated institution scope.

Preferred pattern:

```python
repo = StudentRepository(
    session=session,
    institution_id=institution_id,
)

student = await repo.get_by_id(student_id)
```

Avoid:

```python
student = await repo.get_by_id(
    student_id,
    institution_id,
)
```

when the repository architecture can bind the tenant once.

The goal is to make accidental omission of tenant filtering difficult.

---

# 13. Repository Rules

Repositories are not just database convenience classes.

They enforce important architectural boundaries.

The project uses different repository capabilities.

Conceptually:

```text
BaseRepository
    │
    ├── read operations
    │
    ├── MutableRepository
    │
    ├── EventRepository
    │
    └── DefinitionRepository
```

## EventRepository

Events are append-only.

Examples:

```text
student_backlog_events
student_offer_events
dream_declaration_events
policy_lifecycle_events
```

Allowed:

```text
INSERT
SELECT
```

Not allowed:

```text
UPDATE
DELETE
```

Database triggers also enforce this.

Application-level protection alone is not sufficient.

---

# 14. Definition Immutability

Approved/active definitions are part of the audit trail.

Examples:

```text
Policy Version
Company Requirement Version
```

Once a definition becomes authoritative:

```text
APPROVED
ACTIVE
```

its definition payload cannot simply be rewritten.

Bad:

```text
Policy v1
    ↓
APPROVED
    ↓
Developer edits the original requirements
```

Correct:

```text
Policy v1
    ↓
APPROVED
    ↓
ACTIVE
    ↓
Correction required
    ↓
Policy v2
```

This protects reproducibility.

---

# 15. Why Immutability Matters

Imagine a student was evaluated yesterday.

Yesterday:

```text
CGPA requirement = 7.5
Student CGPA = 7.8
Result = ELIGIBLE
```

If someone silently changes the policy to:

```text
CGPA requirement = 8.0
```

then the old decision can no longer be reproduced.

That is unacceptable for a placement system.

Therefore:

> Historical authoritative definitions must remain reproducible.

---

# 16. Database Constraints Are Important

Do not rely only on Python validation.

Important invariants should also be enforced by PostgreSQL where practical.

Examples:

```text
Foreign keys
Composite foreign keys
Unique constraints
Check constraints
Exclusion constraints
Immutable-history triggers
Definition immutability triggers
Tenant boundaries
```

Application validation provides one layer.

Database constraints provide another layer.

---

# 17. M2 — What It Is

M2 is the:

> **Domain Model / Persistence Layer**

It establishes the database foundation for the placement domain.

M2 is concerned with things such as:

```text
Students
Academic records
Backlogs
Offers
Dream declarations
Companies
Company requirements
Policies
Policy versions
Policy lifecycle
Provenance
Institution boundaries
Persistence invariants
```

M2 does **not** mean the complete placement intelligence system is finished.

---

# 18. M2 Gate Status

The project uses milestone gates.

Important distinction:

```text
IMPLEMENTED
    ≠
ACCEPTED
```

A developer may implement a milestone.

An independent review must verify it.

Only then does the milestone become:

```text
ACCEPTED
```

Current Gate Status:

```text
M1  🟢 CERTIFIED / FROZEN
M2  🟢 CERTIFIED / FROZEN
M3  🟢 CERTIFIED / FROZEN
M4  🟢 CERTIFIED / FROZEN
M5  🟢 CERTIFIED / FROZEN
M6  🟢 CERTIFIED / FROZEN
M7  🟢 UNLOCKED
```

M5 was independently certified at commit `d75ffbb06a9479e8451a44f82af870864cbfb38b`,
per the coordinator's supplied review. The recorded regression is 57/57 passing
(21 M5 + 36 M1–M4). See [certification and evidence caveat](project-status/m5.md):
the collected `test_policy_ambiguity` case has no behavioral assertion and does
not prove the ambiguity branch. The reviewer classified this as non-blocking debt.

M1–M6 are frozen. M6 was independently certified after producing an evidence package demonstrating 92.5% Recall@5, 20/20 abstention accuracy, 100% policy version exactness, and explicit recovery invariants. M7 (Agent Foundation) is now unlocked and implementation may begin following the design gate.
The [M6 RAG contract](contracts/rag-contract.md) and [M6 plan](testing/m6-plan.md) define the gate.
The [M6 status record](project-status/m6.md) separates the implemented source-storage, binding lifecycle, and durable ingestion increments from the certification gate.
Do not reopen certified milestones without a concrete regression or dependency.

Do not mark a milestone `CERTIFIED` based solely on an implementation agent's statement.

---

# 19. M2 Remediation Gates

The previous independent review identified six blocking areas.

```text
B01 — Tenant-scoped repositories
B02 — Append-only event history
B03 — Definition immutability
B04 — Concurrent dream approval limit
B05 — Invariant / negative tests
B06 — Backup / restore validation
```

Each requires implementation **and evidence**.

### B01

Every repository operation must enforce tenant scope.

### B02

Historical events cannot be updated or deleted.

### B03

Approved/active definitions cannot have their authoritative payload rewritten.

### B04

Only one active approved dream company can exist for a student in an academic year.

### B05

Important invariants must have negative tests.

### B06

Database backup and restoration must preserve the M2 persistence contract.

---

# 20. Development Workflow

Before writing code:

```text
1. Read the relevant contract.
2. Identify the invariant.
3. Identify the affected domain model.
4. Identify database implications.
5. Identify repository implications.
6. Identify tests.
7. Implement.
8. Run tests.
9. Update documentation.
10. Produce evidence.
```

Do not follow:

```text
Code first
Documentation later
Tests eventually
```

This project is contract-driven.

---

# 21. Before Making a Change

Ask:

### Question 1

Does this change alter a business rule?

If yes:

```text
STOP
```

Review:

```text
docs/contracts/
```

### Question 2

Does this change affect tenant isolation?

If yes:

Review:

```text
repository
database
authorization
tests
```

### Question 3

Does this change modify an immutable definition?

If yes:

Do not modify the existing version.

Create a new version through the approved lifecycle.

### Question 4

Does this change affect historical events?

If yes:

Events are append-only.

### Question 5

Does this change affect an existing milestone?

Update the corresponding test/evidence documentation.

---

# 22. Testing Philosophy

Tests should prove both:

```text
Happy path
+
Failure path
```

For every important invariant, ask:

> "How do we prove that an invalid operation fails?"

Examples:

```text
Can Institution A read Institution B's student?

Can an event be deleted?

Can an active policy be modified?

Can two dream companies be approved concurrently?

Can invalid CGPA values enter the database?

Can an unresolved compensation value be treated as comparable?
```

These negative tests are as important as successful operations.

---

# 23. Fresh Database Validation

A migration that works on an existing developer database is not sufficient.

Always validate from a clean database when required.

Typical sequence:

```bash
alembic upgrade head
```

Then run the relevant test suite.

For migration integrity:

```bash
alembic downgrade base
alembic upgrade head
```

If applicable, verify:

```bash
alembic revision --autogenerate
```

and confirm there is no unexpected metadata drift.

---

# 24. Backup and Restore

Persistence is not validated until backup and restore are proven.

The M2 validation should demonstrate:

```text
Database A
    ↓
pg_dump
    ↓
Backup
    ↓
Database B
    ↓
pg_restore
    ↓
Compare
```

Comparison should include:

```text
Schema
Rows
Important data
Event history
Constraints
Indexes
Triggers
Projection tables
```

---

# 25. Git Workflow

Work on the appropriate branch.

Before committing:

```bash
git status
git diff
```

Run the relevant tests.

Then:

```bash
git add .
git commit -m "Clear descriptive message"
git push origin dev
```

After pushing:

```bash
git status
git log origin/dev --oneline -5
```

The remote branch is the source of truth for independent review.

---

# 26. Do Not Hide Work From Review

Do not rely on:

```text
"It works locally."
```

Provide reproducible evidence.

Good evidence:

```text
Command
+
Output
+
Relevant file
+
Expected result
```

For example:

```text
pytest tests/test_m2_persistence.py -v

Expected:
all M2 tests pass
```

Better:

```text
Fresh DB
+
Migration
+
Tests
+
Backup
+
Restore
+
Verification
```

---

# 27. Never Self-Certify a Milestone

The implementation developer may say:

> "M2 is complete."

That means:

```text
Implementation status = IMPLEMENTED
```

It does not automatically mean:

```text
Gate status = ACCEPTED
```

The independent reviewer determines acceptance.

This separation exists to prevent:

```text
Implementation
      ↓
Developer says perfect
      ↓
Immediately accepted
```

Instead:

```text
Implementation
      ↓
Evidence
      ↓
Independent review
      ↓
Findings
      ↓
Remediation
      ↓
Independent re-review
      ↓
ACCEPTED
```

---

# 28. Current Project Milestones

The overall roadmap is:

```text
M0  Requirements / Contracts
 ↓
M1  Platform Foundation
 ↓
M2  Domain Model / Persistence
 ↓
M3  Company / Opportunity
 ↓
M4  Policy Lifecycle
 ↓
M5  Deterministic Eligibility
 ↓
R1  Decision MVP
 ↓
M6  Policy RAG
 ↓
R2  Policy Intelligence
 ↓
M7  Agent Foundation
 ↓
M8  Agent Orchestration
 ↓
M9  Student Copilot
 ↓
R3  AI Placement Copilot
 ↓
M10 Security / Hardening
 ↓
M11 Production Readiness / Certification
 ↓
R4 Production
```

Do not skip gates simply because later functionality can technically be developed.

---

# 29. M5 — Deterministic Eligibility Engine

M5 is the:

> **Deterministic Eligibility Decision Engine**

It evaluates whether a student is eligible for a placement opportunity based on two independent constraint domains:

```text
Domain 1: Opportunity Requirements
    (CGPA, backlogs, etc.)
         +
Domain 2: Institutional Policy
    (active offer limits, etc.)
         ↓
Deterministic Evaluation
         ↓
ELIGIBLE / NOT_ELIGIBLE / UNKNOWN
         +
Criterion-level reasons
         +
Immutable decision snapshot
```

### Key Components

```text
evaluator.py          Pure deterministic tri-state evaluator (no DB, no LLM)
eligibility_service.py  Policy selection, snapshot construction, evaluation orchestration
eligibility.py        Router: POST /api/v1/eligibility/evaluate
```

### M5 Invariants

```text
1. Policy selection: institution_id + academic_year_id + scope + activation_window + ACTIVE status
2. 0 matches → NO_ACTIVE_POLICY (400)
3. >1 match → POLICY_AMBIGUITY (500)
4. Snapshot captures authoritative facts at evaluation_time (not live data)
5. Missing/unknown facts → UNKNOWN (never silent PASS or FAIL)
6. Decision algebra: FAIL > UNKNOWN > PASS
7. Decisions are immutable (PL/pgSQL trigger blocks UPDATE/DELETE)
8. Idempotency via SHA256 evaluation_key
9. AI has zero authority over the eligibility result
```

### Snapshot Structure

```text
{
    "student_id": "...",
    "opportunity_id": "...",
    "academic": {
        "cgpa": 8.5,        ← from latest AcademicRecord where cgpa_state = KNOWN
        "backlogs": 1       ← count of open backlogs (latest BacklogEvent.kind = OPENED)
    },
    "placement_history": {
        "active_offer_count": 1  ← count of active offers (latest OfferEvent.kind in RECEIVED/ACCEPTED/TERMS_REVISED)
    }
}
```

### Replay Guarantee

Given the same `snapshot`, `policy_rules`, and `requirement_criteria`, the pure evaluator function **must** produce the identical `result` and `reasons`. This is verified by `test_snapshot_replay`.

---

# 30. Scope Boundaries

The platform is intentionally limited.

The system does **not** automatically:

* apply to companies
* make recruiter decisions
* communicate externally on behalf of students
* schedule interviews
* predict job outcomes
* create an unrestricted multi-agent system

AI is an assistant and orchestrator.

It is not the authority over institutional placement rules.

---

# 31. Interview Preparation Is Out of Scope

Do not add:

```text
Interview preparation
Interview assessment
Skill-gap assessment
Automated interview coaching
```

to the core placement eligibility scope unless the project requirements are formally changed.

The current focus is:

```text
Eligibility
Policy Intelligence
Evidence
Placement Agent Workflows
```

---

# 32. If You Find a Problem

Do not silently work around it.

Use this process:

```text
1. Reproduce the problem.
2. Identify which contract/invariant is affected.
3. Document the finding.
4. Determine whether it blocks the milestone.
5. Implement the smallest correct remediation.
6. Add a regression test.
7. Update evidence.
8. Request independent review.
```

---

# 33. Definition of "Done"

A feature is not done merely because:

```text
the code compiles
```

or:

```text
the API returns 200
```

For this project, "done" generally means:

```text
Contract satisfied
       +
Implementation complete
       +
Tests pass
       +
Security invariants verified
       +
Evidence documented
       +
Independent gate passed
```

---

# 34. New Developer First-Day Checklist

Before making your first pull request:

```text
[ ] Read this onboarding document

[ ] Read README.md

[ ] Understand the architecture

[ ] Read docs/contracts/

[ ] Understand tenant isolation

[ ] Understand immutable events

[ ] Understand immutable definitions

[ ] Understand ELIGIBLE / NOT_ELIGIBLE / UNKNOWN

[ ] Understand previous-offer rules

[ ] Understand dream-company rules

[ ] Understand compensation rules

[ ] Understand the AI agent boundary

[ ] Run the development stack

[ ] Run existing tests

[ ] Inspect the database schema

[ ] Understand Alembic migrations

[ ] Understand repository patterns

[ ] Understand milestone gates

[ ] Never modify authoritative definitions casually

[ ] Never bypass tenant isolation

[ ] Never let the LLM override deterministic eligibility
```

---

# 35. Quick Mental Model

If you remember only one diagram, remember this:

```text
                    USER
                     │
                     ↓
              ┌─────────────┐
              │  Next.js UI │
              └──────┬──────┘
                     │
                     ↓
              ┌─────────────┐
              │   FastAPI   │
              └──────┬──────┘
                     │
             ┌───────┴────────┐
             ↓                ↓
       ┌───────────┐    ┌────────────┐
       │ AI Agent  │    │  Domain /  │
       │           │    │ Application │
       └─────┬─────┘    └──────┬─────┘
             │                 │
             ↓                 ↓
       Authorized Tools   Deterministic
                          Business Rules
                               │
                     ┌─────────┼─────────┐
                     ↓         ↓         ↓
                PostgreSQL   Qdrant    Redis
                     │
                     ↓
               Authoritative
                  State
```

And the most important architectural rule is:

```text
              AI
               │
               ↓
          EXPLAINS / ORCHESTRATES
               │
               X
               │
        CANNOT OVERRIDE
               │
               ↓
     DETERMINISTIC ENGINE
               │
               ↓
       AUTHORITATIVE RESULT
```

---

# 36. Final Rule

When in doubt:

> **Stop, read the contract, identify the invariant, implement defensively, test the failure case, document the evidence, and let the independent gate decide.**

That is the engineering standard for this project.
