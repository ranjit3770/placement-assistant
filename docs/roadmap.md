# AI-Powered Student Placement Intelligence Platform

## Engineering Roadmap

**Roadmap Version:** 2.0
**Based on:** SRS v2.0
**Target Architecture:** Next.js (Typescript, Tailwind css) + FastAPI + PostgreSQL + Redis + Qdrant + OpenAI + Docker
**Development Model:** Gated Engineering Delivery
**Primary Decision Principle:** Deterministic eligibility, AI-assisted orchestration

---

# 1. Roadmap Objective

The objective of this roadmap is to build the AI Placement Intelligence Platform incrementally while ensuring that every release is:

* Testable
* Auditable
* Reproducible
* Secure
* Policy-grounded
* Production-oriented

The project shall not follow:

```text
UI → Chatbot → AI → Business Logic
```

Instead, the project shall follow:

```text
Foundation
    ↓
Domain Model
    ↓
Policy & Business Rules
    ↓
Eligibility Engine
    ↓
Policy RAG
    ↓
AI Agent
    ↓
Student Copilot
    ↓
Administration
    ↓
Production Certification
```

---

# 2. Master Roadmap

```text
M0  Requirements & Contracts
        ↓
M1  Platform Foundation
        ↓
M2  Domain & Database
        ↓
M3  Company & Opportunity Management
        ↓
M4  Policy Lifecycle
        ↓
M5  Deterministic Eligibility Engine
        ↓
R1  Decision MVP
        ↓
M6  Policy RAG
        ↓
R2  Policy Intelligence
        ↓
M7  AI Agent Foundation
        ↓
M8  Agent Tools & Orchestration
        ↓
M9  Student AI Copilot
        ↓
R3  AI Placement Copilot
        ↓
M10 Security, Audit & Production Hardening
        ↓
M11 Production Readiness & Certification
        ↓
R4  Production Release
```

---

# 3. Phase Summary

| Phase | Name                     | Primary Outcome                          |
| ----- | ------------------------ | ---------------------------------------- |
| M0    | Requirements & Contracts | Authoritative engineering baseline       |
| M1    | Platform Foundation      | Running full-stack infrastructure        |
| M2    | Domain & Database        | Authoritative data model                 |
| M3    | Company & Opportunity    | Company requirements platform            |
| M4    | Policy Lifecycle         | Versioned approved policy system         |
| M5    | Eligibility Engine       | Deterministic decision engine            |
| R1    | Decision MVP             | First usable placement decision platform |
| M6    | Policy RAG               | Policy retrieval and evidence            |
| R2    | Policy Intelligence      | AI-assisted policy knowledge             |
| M7    | Agent Foundation         | Controlled AI Agent                      |
| M8    | Agent Orchestration      | Tool-based eligibility workflow          |
| M9    | Student Copilot          | Student-facing AI assistant              |
| R3    | AI Placement Copilot     | Complete AI-assisted platform            |
| M10   | Hardening                | Security, reliability, observability     |
| M11   | Certification            | Production validation                    |
| R4    | Production               | Production deployment                    |

---

# 4. M0 — Requirements & Engineering Contracts

## Objective

Freeze the requirements before implementation.

### Deliverables

```text
docs/
├── srs/
│   └── srs.md
│
├── contracts/
│   ├── domain-model.md
│   ├── business-rules.md
│   ├── policy-lifecycle.md
│   ├── eligibility-contract.md
│   ├── agent-contract.md
│   ├── rag-contract.md
│   ├── security-contract.md
│   └── release-scope.md
│
└── roadmap.md
```

### Define

* Student domain
* Company domain
* Opportunity domain
* Offer model
* Dream-company model
* Policy model
* Rule model
* Eligibility model
* Evidence model
* Agent model

### Gate

M0 passes when:

```text
SRS approved
+
Contracts consistent
+
No unresolved business-rule conflicts
+
Scope frozen
```

---

# 5. M1 — Platform Foundation

## Objective

Create the deployable engineering foundation.

### Backend

```text
FastAPI
Python
Pydantic
SQLAlchemy
Alembic
```

### Frontend

```text
Next.js
TypeScript
App Router
```

### Infrastructure

```text
PostgreSQL
Redis
Qdrant
Docker
Docker Compose
Nginx
```

### Engineering

```text
Environment configuration
Logging
Health checks
Error handling
CI pipeline
```

### Initial endpoints

```text
GET /health
GET /ready
```

### Gate

```text
docker compose up
```

must start all required services successfully.

---

# 6. M2 — Domain & Database

## Objective

Implement the authoritative data model.

### Student

```text
students
student_academic_records
student_semester_records
student_backlogs
student_skills
student_certifications
```

### Placement

```text
student_offers
student_offer_events
student_dream_companies
```

### Company

```text
companies
company_roles
placement_opportunities
company_requirements
company_requirement_versions
```

### Policy

```text
policies
policy_versions
policy_rules
policy_documents
policy_source_locators
```

### Eligibility

```text
eligibility_checks
eligibility_snapshots
eligibility_criteria_results
eligibility_evidence
```

### AI

```text
agent_sessions
agent_messages
agent_tool_calls
```

### Audit

```text
audit_logs
administrative_overrides
```

### Gate

All:

* migrations
* relationships
* constraints
* versioning
* provenance

must have automated tests.

---

# 7. M3 — Company & Opportunity Management

## Objective

Allow placement staff to configure recruitment opportunities.

### Features

```text
Create company
Update company
Create role
Create placement opportunity
Configure package
Configure eligibility criteria
Publish requirement version
Close opportunity
```

### Example

```text
IBM
 └── Software Engineer
      └── 2026 Campus Drive
           └── Requirement v1
```

### Requirements

Support:

```text
SSLC
HSC
CGPA
SGPA
Backlogs
Degree
Department
Graduation year
Package
```

### Gate

A coordinator can create a complete placement opportunity and publish its requirements.

---

# 8. M4 — Policy Lifecycle

## Objective

Make institutional placement policy authoritative and versioned.

### Workflow

```text
UPLOAD
   ↓
PROCESS
   ↓
REVIEW
   ↓
APPROVE
   ↓
ACTIVATE
   ↓
ARCHIVE
```

### Features

* Policy upload
* Policy versioning
* Source preservation
* Hashing
* Effective dates
* Approval
* Activation
* Deactivation
* Archiving

### Critical Rule

An uploaded document is **not automatically an executable policy**.

Correct workflow:

```text
Document
 ↓
Extract
 ↓
Candidate Rules
 ↓
Human Review
 ↓
Approved Rules
 ↓
Active Policy
```

### Gate

Historical active policies cannot be mutated.

---

# 9. M5 — Deterministic Eligibility Engine

## Objective

Build the most important component of the system.

The engine shall determine:

```text
ELIGIBLE
NOT_ELIGIBLE
UNKNOWN
```

### Inputs

```text
Student Snapshot
+
Opportunity Snapshot
+
Requirement Version
+
Policy Version
+
Placement History
+
Dream Declaration
```

### Rules

Implement:

```text
Academic
Backlog
Degree
Department
Graduation
Package
Placement history
Dream company
Exceptions
```

---

# 10. Academic Rule Engine

Implement operators:

```text
>
>=
<
<=
=
!=
IN
NOT_IN
BETWEEN
```

Example:

```text
CGPA >= 7.0
```

Test:

```text
7.0 → PASS
7.1 → PASS
6.9 → FAIL
```

---

# 11. Package Rule Engine

Implement:

```text
Previous Accepted Offer
        ↓
New Opportunity Package
```

Normal company:

```text
new > previous
```

Dream company:

```text
new >= previous
```

Only if explicitly authorized by active policy.

---

# 12. Eligibility Aggregation

Example:

```text
SSLC        PASS
HSC         PASS
CGPA        PASS
Backlogs    PASS
Degree      PASS
Department  PASS
Package     PASS
Policy      PASS
```

Result:

```text
ELIGIBLE
```

Any mandatory failure:

```text
NOT_ELIGIBLE
```

Required information unavailable:

```text
UNKNOWN
```

---

# 13. M5 Gate

M5 is complete only when:

```text
100% critical business rules tested
+
Boundary cases tested
+
Negative cases tested
+
Unknown cases tested
+
Replay verified
+
API verified
```

At this point, the core eligibility system exists **without AI**.

---

# 14. R1 — Decision MVP

R1 is the first usable product.

It contains:

```text
Student
+
Company
+
Opportunity
+
Policy
+
Placement History
+
Eligibility Engine
+
Decision API
+
Audit
+
Replay
```

### Student can:

```text
Check company eligibility
View reasons
View failed criteria
View package restriction
View decision time
```

### Coordinator can:

```text
Manage students
Manage companies
Manage requirements
Review decisions
```

---

# 15. M6 — Policy RAG

## Objective

Add policy knowledge retrieval.

### Supported documents

```text
PDF
Markdown
TXT
```

### Pipeline

```text
Document
 ↓
Parser
 ↓
Normalizer
 ↓
Chunker
 ↓
Metadata
 ↓
Embedding
 ↓
Qdrant
```

---

# 16. RAG Metadata

Every chunk should preserve:

```text
document_id
policy_id
policy_version
academic_year
section
page
chunk_id
content_hash
```

---

# 17. Retrieval

Implement:

```text
Semantic Search
+
Metadata Filtering
+
Policy Version Filtering
+
Academic Year Filtering
```

Optional later:

```text
Reranking
Hybrid Search
```

---

# 18. Evidence

Every policy answer should identify:

```text
Document
Version
Section
Page
Relevant text
```

The user should be able to understand where the answer came from.

---

# 19. RAG Evaluation

Create a fixed evaluation dataset.

Example:

```text
Question
Expected Policy
Expected Section
Expected Evidence
```

Measure:

```text
Retrieval accuracy
Evidence relevance
Version accuracy
Citation accuracy
```

---

# 20. M6 Gate

RAG passes when:

```text
Correct policy retrieved
+
Correct policy version retrieved
+
Correct evidence surfaced
+
Historical policy does not incorrectly override active policy
```

---

# 21. R2 — Policy Intelligence

R2 introduces AI-assisted policy knowledge.

Capabilities:

```text
Policy Q&A
Policy explanation
Evidence summarization
Validated AI explanations
```

Example:

> "Why can't I attend another 5 LPA company?"

The system retrieves the policy and explains it.

AI does not modify eligibility.

---

# 22. M7 — AI Agent Foundation

## Objective

Introduce the single student-aware AI Agent.

Architecture:

```text
User
 ↓
Agent
 ↓
Tool Registry
 ↓
Application Services
 ↓
Domain
```

### Agent components

```text
Intent
State
Tool Registry
Guardrails
Prompt Management
Response Validation
```

---

# 23. Agent Tools

Initial read-only tools:

```text
get_student_profile
get_student_academics
get_student_placement_history
get_student_dream_companies

get_company
get_opportunity
get_company_requirements

search_policy
get_policy_evidence
get_active_policy

evaluate_academic_rules
evaluate_package_rule
evaluate_eligibility
```

---

# 24. Agent Security

The Agent shall not:

```text
Access SQL directly
Modify database directly
Modify policy
Modify eligibility
Modify company requirements
Declare dream company automatically
```

All actions go through authorized tools.

---

# 25. M8 — Agent Orchestration

## Objective

Make the Agent capable of completing eligibility workflows.

Example:

```text
Student:
"Am I eligible for IBM?"
```

Agent:

```text
Identify IBM
 ↓
Get student
 ↓
Get academic data
 ↓
Get placement history
 ↓
Get IBM requirements
 ↓
Get applicable policy
 ↓
Call eligibility engine
 ↓
Receive decision
 ↓
Get evidence
 ↓
Generate explanation
```

---

# 26. Agent Response Validation

The Agent output shall be compared with the deterministic engine.

Example:

```text
Engine:
ELIGIBLE

LLM:
ELIGIBLE
```

Valid.

If:

```text
Engine:
NOT_ELIGIBLE

LLM:
ELIGIBLE
```

the response must be rejected and regenerated/fallback to structured output.

---

# 27. M9 — Student AI Copilot

## Objective

Create the student-facing AI experience.

Supported queries:

```text
Am I eligible for IBM?

Why am I not eligible?

Which companies can I attend?

Can I attend a 5 LPA company?

Is IBM my dream company?

What does the placement policy say?

What are my current placement restrictions?
```

---

# 28. Eligible Opportunity Discovery

Student:

> "Which companies can I attend?"

Workflow:

```text
Load current student snapshot
 ↓
Load active opportunities
 ↓
Evaluate eligibility
 ↓
Filter ELIGIBLE
 ↓
Apply deterministic ordering
 ↓
Return results
```

Unknown opportunities shall not be presented as eligible.

---

# 29. Preparation Assistance

Where enabled:

```text
Eligible
    ↓
Preparation Plan

Not Eligible
    ↓
Reason + Future Preparation

Unknown
    ↓
Clarification / Coordinator Review
```

Preparation assistance must never modify eligibility.

---

# 30. R3 — AI Placement Copilot

R3 combines:

```text
Deterministic Eligibility
+
Policy RAG
+
AI Agent
+
Student Context
+
Company Discovery
+
AI Explanation
+
Conversation
```

This is the main AI product milestone.

---

# 31. M10 — Security & Production Hardening

## Objective

Harden the entire platform.

### Security

```text
Authentication
Authorization
RBAC
Rate limiting
TLS
CORS
Security headers
Secret management
File validation
Prompt injection protection
Tool authorization
```

---

# 32. Agent Security Testing

Test:

```text
Prompt injection
Tool abuse
Unauthorized data access
Cross-student access
Tool argument manipulation
Policy injection
Data exfiltration attempts
```

---

# 33. Data Security

Verify:

```text
Student A cannot access Student B
Student cannot access admin functions
Agent cannot bypass authorization
Logs do not expose sensitive information
OpenAI receives only required information
```

---

# 34. Observability

Implement:

```text
Request ID
Trace ID
Structured logs
API metrics
Agent traces
Tool traces
RAG metrics
Eligibility metrics
Worker metrics
```

---

# 35. Reliability

Implement:

```text
Health checks
Readiness checks
Timeouts
Retries
Circuit breakers where appropriate
Graceful AI failure
Graceful RAG failure
Worker retry handling
```

---

# 36. M11 — Production Readiness & Certification

This is the final engineering validation phase.

The implementation team shall not self-certify release labels.

Validation should be evidence-based and independently reviewed.

---

# 37. M11 Validation Areas

## Functional

```text
Student
Company
Opportunity
Policy
Eligibility
Agent
RAG
Admin
```

## Security

```text
Authentication
Authorization
PII protection
Prompt injection
Tool security
File upload
Secrets
```

## Performance

```text
API latency
Eligibility latency
RAG latency
Agent latency
Concurrent users
Database load
```

## Reliability

```text
Restart
Failure
Recovery
Backup
Restore
Dependency outage
```

---

# 38. Replay Certification

Take a completed historical eligibility decision.

Re-run it using:

```text
Student Snapshot
+
Requirement Version
+
Policy Version
+
Rule Engine Version
```

Expected:

```text
Same Decision
+
Same Criterion Results
+
Same Policy Evidence
```

---

# 39. AI Certification

Test the Agent against a fixed benchmark.

Example:

```text
100 student/company eligibility questions
```

Validate:

```text
Correct student
Correct company
Correct tools
Correct policy
Correct eligibility
Correct explanation
No hallucinated requirements
No unauthorized actions
```

---

# 40. RAG Certification

Test:

```text
Known policy questions
Ambiguous questions
Historical-policy questions
Missing-policy questions
Conflicting-policy questions
```

Expected behavior must be defined beforehand.

---

# 41. Production Gate

Production release requires:

```text
Functional tests PASS
+
Security tests PASS
+
Agent evaluation PASS
+
RAG evaluation PASS
+
Performance PASS
+
Backup PASS
+
Restore PASS
+
Observability PASS
+
Documentation PASS
+
Independent review PASS
```

---

# 42. R4 — Production Release

Production deployment:

```text
Internet / Institutional Network
          │
          ▼
       Nginx
          │
     ┌────┴────┐
     ▼         ▼
 Next.js     FastAPI
                │
       ┌────────┼─────────┐
       ▼        ▼         ▼
   PostgreSQL Redis     Qdrant
                │
                ▼
             Worker
                │
                ▼
             OpenAI
```

---

# 43. Deployment Environments

Maintain separate environments:

```text
development
staging
production
```

Never test production business-rule changes directly.

---

# 44. Environment Promotion

```text
Development
     ↓
CI
     ↓
Automated Tests
     ↓
Staging
     ↓
Acceptance
     ↓
Production
```

---

# 45. CI/CD Roadmap

## CI

Every pull request:

```text
Lint
 ↓
Type Check
 ↓
Unit Tests
 ↓
Integration Tests
 ↓
Security Scan
 ↓
Docker Build
```

## CD

After approval:

```text
Build
 ↓
Tag
 ↓
Deploy Staging
 ↓
Smoke Tests
 ↓
Approval
 ↓
Production
```

---

# 46. Milestone Deliverables

| Milestone | Deliverable              |
| --------- | ------------------------ |
| M0        | Requirements + Contracts |
| M1        | Running infrastructure   |
| M2        | Database/domain          |
| M3        | Company requirements     |
| M4        | Policy lifecycle         |
| M5        | Eligibility engine       |
| R1        | Decision MVP             |
| M6        | RAG                      |
| R2        | Policy Intelligence      |
| M7        | Agent foundation         |
| M8        | Agent orchestration      |
| M9        | Student Copilot          |
| R3        | AI Placement Copilot     |
| M10       | Security/hardening       |
| M11       | Certification            |
| R4        | Production               |

---

# 47. Recommended Implementation Priority

The priority should be:

```text
P0 — Eligibility correctness
P0 — Policy correctness
P0 — Data correctness
P0 — Security

P1 — RAG
P1 — Agent orchestration
P1 — Student experience

P2 — Analytics
P2 — Preparation
P2 — Advanced recommendations
```

Do not allow P2 features to delay the core decision engine.

---

# 48. Critical Dependencies

```text
M1
 ↓
M2
 ↓
M3
 ↓
M4
 ↓
M5
 ↓
R1
 ↓
M6
 ↓
R2
 ↓
M7
 ↓
M8
 ↓
M9
 ↓
R3
 ↓
M10
 ↓
M11
 ↓
R4
```

The most important dependency is:

```text
M4 Policy Lifecycle
       ↓
M5 Eligibility Engine
       ↓
M7/M8 Agent
```

The Agent should not become the place where business rules are implemented.

---

# 49. Parallel Workstreams

Once M2 is stable, some work can proceed in parallel.

```text
                    M2
                     │
        ┌────────────┼─────────────┐
        │            │             │
        ▼            ▼             ▼
    Company       Policy        Frontend
    Module        Module        Foundation
        │            │             │
        └────────────┼─────────────┘
                     ▼
                    M5
```

Similarly:

```text
M5
 │
 ├── API
 ├── RAG
 ├── UI
 └── Agent foundation
```

But the final Agent eligibility workflow depends on the deterministic engine being stable.

---

# 50. Definition of Done per Milestone

Every milestone must have:

```text
Requirements
    ↓
Implementation
    ↓
Tests
    ↓
Negative Tests
    ↓
Security
    ↓
Observability
    ↓
Documentation
    ↓
Evidence
    ↓
Gate Review
```

A Git commit or working demo is not sufficient evidence of completion.

---

# 51. Project Status Model

Use these statuses:

```text
NOT_STARTED
IN_PROGRESS
IMPLEMENTED
TESTING
VALIDATION
ACCEPTED
BLOCKED
REJECTED
```

Do not use:

```text
COMPLETE
```

until the acceptance gate has passed.

---

# 52. Suggested Git Branch Strategy

```text
main
 │
 ├── develop
 │
 ├── feature/student-domain
 ├── feature/company-requirements
 ├── feature/policy-lifecycle
 ├── feature/eligibility-engine
 ├── feature/rag
 ├── feature/agent
 └── feature/copilot
```

Production releases should be tagged.

Example:

```text
v0.1.0
v0.2.0
v1.0.0
```

---

# 53. Recommended Documentation Structure

```text
docs/
│
├── srs/
│   └── srs-v2.md
│
├── contracts/
│   ├── domain-model.md
│   ├── business-rules.md
│   ├── policy-lifecycle.md
│   ├── eligibility-contract.md
│   ├── agent-contract.md
│   ├── rag-contract.md
│   └── security-contract.md
│
├── architecture/
│   ├── system-architecture.md
│   ├── database.md
│   ├── agent.md
│   └── rag.md
│
├── testing/
│   ├── test-strategy.md
│   ├── eligibility-tests.md
│   ├── rag-evaluation.md
│   └── agent-evaluation.md
│
├── operations/
│   ├── deployment.md
│   ├── backup.md
│   ├── restore.md
│   └── incident-response.md
│
└── roadmap.md
```

---

# 54. Core Engineering Gates

The project has five major gates.

## Gate G1 — Data Integrity

```text
Student
+
Company
+
Policy
+
Placement
```

must be correct.

---

## Gate G2 — Decision Correctness

```text
Eligibility Engine
```

must be deterministic and fully tested.

---

## Gate G3 — Evidence Correctness

```text
RAG
+
Policy Evidence
```

must retrieve the correct authoritative information.

---

## Gate G4 — Agent Correctness

```text
Agent
+
Tools
+
Eligibility
+
Evidence
```

must produce validated responses.

---

## Gate G5 — Production Certification

```text
Security
+
Performance
+
Reliability
+
Backup
+
Restore
+
Observability
+
Independent Validation
```

must pass.

---

# 55. Final Roadmap

The complete engineering journey is:

```text
                         AI PLACEMENT PLATFORM

                              M0
                    Requirements & Contracts
                              │
                              ▼
                              M1
                    Platform Foundation
                              │
                              ▼
                              M2
                     Domain & PostgreSQL
                              │
                              ▼
                              M3
                 Company & Opportunity Model
                              │
                              ▼
                              M4
                     Policy Lifecycle
                              │
                              ▼
                              M5
                 Deterministic Eligibility
                              │
                              ▼
                             R1
                     DECISION MVP
                              │
                              ▼
                              M6
                       Policy RAG
                              │
                              ▼
                             R2
                  POLICY INTELLIGENCE
                              │
                              ▼
                              M7
                    AI Agent Foundation
                              │
                              ▼
                              M8
                  Agent Tool Orchestration
                              │
                              ▼
                              M9
                     Student Copilot
                              │
                              ▼
                             R3
                  AI PLACEMENT COPILOT
                              │
                              ▼
                             M10
                 Security & Hardening
                              │
                              ▼
                             M11
              Production Readiness & Certification
                              │
                              ▼
                             R4
                    PRODUCTION RELEASE
```

---

# 56. Final Engineering Rule

The project shall always maintain this separation:

```text
                 ┌─────────────────────┐
                 │      AI AGENT       │
                 │                     │
                 │ Understand          │
                 │ Orchestrate         │
                 │ Retrieve            │
                 │ Explain             │
                 └──────────┬──────────┘
                            │
                       Authorized Tools
                            │
                            ▼
                 ┌─────────────────────┐
                 │ APPLICATION LAYER   │
                 └──────────┬──────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │ ELIGIBILITY ENGINE  │
                 │                     │
                 │ DETERMINISTIC       │
                 │ AUTHORITATIVE       │
                 └──────────┬──────────┘
                            │
                            ▼
                ELIGIBLE / NOT / UNKNOWN
```

The Agent **never becomes the business-rule engine**.

The RAG system **never becomes the business-rule engine**.

The frontend **never becomes the business-rule engine**.

The PostgreSQL database **stores authoritative facts but does not itself decide eligibility**.

The **Eligibility Engine** is the authoritative decision component.
