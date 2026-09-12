# Software Requirements Specification

# AI-Powered Student Placement Intelligence Platform

**Version:** 2.0
**Date:** 2026-09-12
**Status:** Proposed Authoritative Engineering Baseline
**Architecture:** AI-Agent + Deterministic Eligibility Engine + Policy RAG
**Frontend:** Next.js  (Typescript, Tailwind css)
**Backend:** FastAPI
**Primary Database:** PostgreSQL
**Vector Database:** Qdrant
**Cache / Infrastructure:** Redis
**Deployment:** Docker / Docker Compose
**LLM Provider:** OpenAI API
**Document Formats:** PDF, Markdown, TXT

---

# 1. Document Authority

This Software Requirements Specification (SRS) defines the authoritative functional, architectural, business, security, AI, data, and operational requirements for the **AI-Powered Student Placement Intelligence Platform**.

This document supersedes earlier informal project descriptions and draft requirements.

Implementation artifacts, prototypes, conversations, examples, prompts, and historical documents do not override this SRS unless they are explicitly incorporated through the project's requirements-change process.

This SRS defines **what the system must do**.

Detailed implementation contracts may be maintained separately where required, including:

* Domain Model
* Business Rules
* Policy Lifecycle
* Eligibility Contract
* Agent Contract
* RAG Contract
* Security Contract
* Release Scope
* Roadmap

These documents must remain consistent with this SRS.

A conflict between normative contracts shall block implementation of the affected behavior until the conflict is formally resolved.

---

# 2. Product Definition

The platform is a web-based student placement intelligence system that determines whether an individual student is eligible to participate in a specific company placement opportunity.

The system combines:

```text
Verified Student Facts
        +
Company Requirements
        +
Approved Placement Policy
        +
Placement History
        +
Authorized Exceptions
        ↓
Deterministic Eligibility Engine
        ↓
Eligibility Decision
        ↓
Policy Evidence
        ↓
AI Agent / Explanation Layer
        ↓
Student-facing Response
```

The system is therefore **not primarily a chatbot**.

It is a:

> **Policy-aware, deterministic placement decision platform with an AI Agent interface.**

---

# 3. Core Architectural Principle

The following invariant is mandatory:

> **AI may orchestrate, retrieve, explain, and assist; AI shall not independently determine or modify eligibility.**

The authoritative eligibility decision must be produced by deterministic backend logic operating on approved rules and a consistent snapshot of authoritative data.

The LLM shall never be allowed to:

* Invent eligibility criteria
* Modify student facts
* Modify company requirements
* Create placement rules
* Override deterministic evaluation
* Convert an unknown result into an eligible result
* Treat arbitrary retrieved text as executable policy
* Directly modify the eligibility result

---

# 4. Product Goals

The platform shall:

1. Centralize student placement information.
2. Maintain verified student academic and placement records.
3. Maintain company requirements and placement opportunities.
4. Manage institutional placement policies.
5. Preserve policy documents and their provenance.
6. Convert approved policy definitions into executable deterministic rules.
7. Evaluate student eligibility consistently.
8. Apply package progression rules.
9. Support authorized dream-company exceptions.
10. Retrieve policy evidence using RAG.
11. Provide an AI Agent capable of interacting with authorized tools.
12. Explain decisions using verified facts and policy evidence.
13. Preserve complete decision provenance.
14. Support deterministic replay.
15. Provide administrative controls.
16. Support production deployment using Docker.
17. Operate safely when AI or vector retrieval services are unavailable.

---

# 5. Non-Goals

The initial platform shall not provide:

* Automated job applications
* Automatic recruiter decisions
* Automated communication with companies
* Interview scheduling
* Placement outcome prediction
* Guaranteed job recommendations
* Multi-agent orchestration
* Autonomous external actions
* Interview preparation as a mandatory core capability
* Aptitude preparation
* Resume generation
* Resume scoring
* Generic career coaching

Preparation assistance may be introduced as an explicitly scoped R3/R4 capability, but it shall not alter eligibility.

---

# 6. Users and Roles

## 6.1 Student

A student can:

* View their verified profile.
* View academic information.
* View placement history.
* Declare authorized preferences.
* Register dream companies where permitted.
* Check eligibility for a company.
* Ask placement-policy questions.
* Ask why they are ineligible.
* View eligible opportunities.
* View decision evidence.
* View historical eligibility checks.
* Request preparation assistance where enabled.

---

## 6.2 Placement Coordinator

A placement coordinator can:

* Manage student records within authorization scope.
* Manage companies.
* Manage placement opportunities.
* Configure company requirements.
* Submit requirements for approval.
* Upload policy documents.
* Review policy extraction.
* Approve policy definitions where authorized.
* Activate approved policy versions.
* Review eligibility decisions.
* Review audit records.
* Apply authorized administrative overrides.

---

## 6.3 Administrator

An administrator can:

* Manage users.
* Manage roles.
* Manage institutions.
* Manage policy lifecycle.
* Manage system configuration.
* Manage AI configuration.
* Manage retention.
* Review audit logs.
* Manage deployment configuration.
* Manage authorized overrides.

---

# 7. Authority Hierarchy

The platform shall distinguish between different classes of information.

## 7.1 Authoritative Student Facts

Stored in PostgreSQL and verified through the institution's data process.

Examples:

```text
SSLC percentage
HSC percentage
CGPA
SGPA
Backlogs
Degree
Department
Graduation year
Placement offers
Accepted offers
Dream-company declarations
```

---

## 7.2 Company Requirements

Company requirements define the criteria associated with a placement opportunity.

Examples:

```text
Minimum SSLC
Minimum HSC
Minimum CGPA
Maximum backlog count
Eligible degree
Eligible department
Graduation year
Package
Other approved criteria
```

---

## 7.3 Institutional Policy

Institutional policy defines placement-wide rules.

Examples:

```text
Package progression
Offer restrictions
Dream-company exceptions
Backlog rules
Participation rules
Eligibility exceptions
```

---

## 7.4 Policy Documents

Documents such as:

```text
PDF
Markdown
TXT
```

are source material.

Documents are **not automatically executable rules**.

A document must pass the approved policy lifecycle before its rules can become authoritative.

---

# 8. Functional Requirements

## FR-001 — Student Data

The system shall maintain verified student records including:

* Identity
* Academic records
* Semester results
* Skills
* Certifications
* Backlogs
* Placement history
* Offers
* Preferences
* Dream-company declarations

Each material revision shall maintain provenance.

---

## FR-002 — Academic Records

The system shall support:

```text
SSLC percentage
HSC percentage
Diploma percentage
CGPA
SGPA
Semester-wise scores
Graduation year
Degree
Department
```

Academic records shall be versionable.

---

## FR-003 — Placement History

The system shall maintain:

* Company
* Role
* Offer status
* Offer date
* Package
* Currency/unit
* Accepted/rejected status
* Relevant placement event
* Source/provenance

The system shall distinguish between:

```text
Offer received
Offer accepted
Offer rejected
Offer withdrawn
Offer expired
```

The applicable policy shall define which state affects placement eligibility.

---

# 9. Offer Selection

The system shall determine the applicable previous offer according to the approved business rules.

It shall not simply assume:

```text
latest offer = applicable offer
```

The system must support policy-defined selection.

The selected offer must be included in the decision provenance.

Example:

```text
Applicable Previous Offer:
Company: Infosys
Package: ₹5 LPA
Offer Status: Accepted
Selection Rule: Highest accepted offer
```

---

# 10. Company Management

The system shall maintain:

```text
Company
Role
Placement Opportunity
Drive
Package
Requirements
Application deadline
Drive date
Status
```

Each company requirement set shall be versioned.

---

# 11. Placement Opportunities

A placement opportunity represents a specific recruitment opportunity.

Example:

```text
Company: IBM
Role: Software Engineer
Package: ₹5 LPA
Drive: 2026 Campus Drive
Requirement Version: IBM-2026.1
```

Eligibility shall be evaluated against the specific opportunity rather than merely the company name where multiple roles or drives exist.

---

# 12. Company Requirement Rules

Requirements shall support:

### Numeric

```text
SSLC >= 70
HSC >= 65
CGPA >= 7.0
```

### Equality

```text
Degree = B.E
```

### Set membership

```text
Department IN [CSE, IT, ECE]
```

### Boolean

```text
Active Backlogs = false
```

### Range

```text
Graduation Year BETWEEN 2026 AND 2027
```

---

# 13. Requirement Completeness

A company opportunity shall not be evaluated as definitively eligible/ineligible when mandatory requirements are missing.

Example:

```text
CGPA requirement missing
```

shall not silently mean:

```text
No CGPA requirement
```

The requirement must explicitly state whether a criterion is:

```text
Required
Not Applicable
Optional
Unknown
```

---

# 14. Placement Policy Management

The system shall support institutional placement policies.

A policy shall have:

```text
Policy ID
Policy name
Academic year
Version
Effective date
Expiry date
Status
Owner
Approver
Source document
```

---

# 15. Policy Lifecycle

Policy lifecycle shall be:

```text
DRAFT
   ↓
PROCESSING
   ↓
REVIEW
   ↓
APPROVED
   ↓
ACTIVE
   ↓
ARCHIVED
```

Only approved policies may become active.

Activation shall be atomic.

---

# 16. Immutable Policy Definitions

Once a policy version becomes active, its definition shall be immutable.

Corrections require a new version.

Example:

```text
Placement Policy 2026.1
        ↓
Placement Policy 2026.2
```

The system shall never silently mutate historical policy definitions.

---

# 17. Policy Documents

The system shall support:

```text
PDF
Markdown
TXT
```

Each uploaded document shall preserve:

* Original file
* File hash
* Filename
* Upload timestamp
* Uploader
* Source
* Version
* Document type
* Processing status

---

# 18. Policy Source Provenance

Every executable policy rule should have a source locator where applicable.

Example:

```text
Document:
placement-policy-2026.pdf

Version:
2026.1

Page:
12

Section:
4.3

Source Hash:
abc123...
```

This permits a reviewer to determine where a rule originated.

---

# 19. Policy-to-Rule Conversion

The platform shall distinguish:

```text
Source Document
        ↓
Extracted Content
        ↓
Candidate Rule
        ↓
Human Review
        ↓
Approved Rule
        ↓
Active Rule
```

LLM extraction may assist in identifying candidate rules.

LLM output shall not automatically become executable policy.

---

# 20. Policy RAG

The system shall provide retrieval over approved/preserved policy documents.

RAG shall support:

* Semantic retrieval
* Metadata filtering
* Policy version filtering
* Academic-year filtering
* Section/page references
* Source evidence
* Retrieval traceability

---

# 21. Vector Database

Qdrant shall store document embeddings and associated metadata.

Example metadata:

```text
document_id
policy_id
policy_version
academic_year
section
page
chunk_id
content_hash
status
```

Only authorized policy content should be retrievable.

---

# 22. RAG Retrieval Rules

RAG shall prioritize:

1. Active policy
2. Applicable academic year
3. Applicable institution
4. Applicable policy scope
5. Relevant section
6. Company-specific policy where applicable

Historical documents shall not override active policy unless the requested historical evaluation explicitly requires them.

---

# 23. RAG Failure

If policy evidence is required but unavailable, the system shall not fabricate an answer.

The eligibility result may become:

```text
UNKNOWN
```

or:

```text
REVIEW_REQUIRED
```

depending on the eligibility contract.

---

# 24. Eligibility Engine

The Eligibility Engine shall be deterministic.

It shall evaluate:

```text
Student Facts
+
Company Requirements
+
Applicable Policy Rules
+
Placement History
+
Authorized Exceptions
```

---

# 25. Eligibility Result States

The system shall support exactly three primary decision states:

```text
ELIGIBLE
NOT_ELIGIBLE
UNKNOWN
```

`UNKNOWN` shall be used where a definitive decision cannot safely be made.

Examples:

* Missing mandatory student data
* Missing mandatory company requirement
* Missing applicable policy
* Conflicting active definitions
* Unresolved policy interpretation

---

# 26. Criterion-Level Results

Each evaluated criterion shall produce:

```json
{
  "criterion": "CGPA",
  "student_value": 7.5,
  "required_value": 7.0,
  "operator": ">=",
  "result": "PASS"
}
```

Possible criterion states:

```text
PASS
FAIL
UNKNOWN
NOT_APPLICABLE
```

---

# 27. Academic Eligibility

Example:

```text
Student:
SSLC = 75%

Company:
Minimum SSLC = 70%
```

Evaluation:

```text
75 >= 70
PASS
```

The same mechanism shall apply to:

* HSC
* CGPA
* SGPA
* Diploma
* Backlogs
* Degree
* Department
* Graduation year

where required.

---

# 28. Package Progression Policy

The system shall support the institutional package progression rule.

Default example:

```text
Previous accepted package = ₹5 LPA
```

For a normal company:

```text
new_package > 5 LPA
```

For an authorized dream-company exception:

```text
new_package >= 5 LPA
```

Therefore:

| New Package | Normal Company | Dream Company |
| ----------: | -------------- | ------------- |
|      ₹3 LPA | NOT_ELIGIBLE   | NOT_ELIGIBLE  |
|      ₹4 LPA | NOT_ELIGIBLE   | NOT_ELIGIBLE  |
|      ₹5 LPA | NOT_ELIGIBLE   | ELIGIBLE*     |
|      ₹6 LPA | ELIGIBLE       | ELIGIBLE      |

`*` only when the active policy explicitly authorizes the dream-company exception.

---

# 29. Dream Company

The system shall maintain explicit student dream-company declarations.

A dream-company declaration shall have:

```text
student_id
company_id
declared_at
status
source
```

A routine eligibility query shall be read-only.

Checking:

> "Am I eligible for IBM?"

must not automatically declare IBM as a dream company.

---

# 30. Dream Company Locking

Any operation that creates or changes a dream-company declaration shall be an explicit user action.

Example:

```text
POST /students/{id}/dream-companies
```

must represent an explicit declaration.

The AI Agent shall not perform such a mutation merely because a student says:

> "IBM is my dream company."

unless the user explicitly invokes the supported declaration action and authorization requirements are satisfied.

---

# 31. Dream Exception

A dream-company declaration alone does not guarantee an exception.

The engine must verify:

```text
Dream declaration exists
        AND
Active policy permits exception
        AND
Company is eligible for exception
        AND
No unrelated rule fails
```

Only then can equal-package participation be allowed.

---

# 32. Exceptions

Exceptions shall be explicit and typed.

Example:

```text
DREAM_COMPANY_EQUAL_PACKAGE
```

Exceptions shall:

* Be authorized
* Be policy-backed
* Be auditable
* Not bypass unrelated eligibility criteria

An exception must never mean:

```text
Ignore all other requirements
```

---

# 33. Eligibility Aggregation

Example:

```text
SSLC       PASS
HSC        PASS
CGPA       PASS
Backlogs   PASS
Degree     PASS
Package    PASS
Policy     PASS
```

Result:

```text
ELIGIBLE
```

If any mandatory rule fails:

```text
NOT_ELIGIBLE
```

If a required rule cannot be evaluated:

```text
UNKNOWN
```

The exact aggregation rules shall be defined in the Eligibility Contract.

---

# 34. Eligibility Snapshot

Each eligibility check shall operate against one consistent snapshot.

The snapshot shall include:

```text
Student version
Academic version
Placement-history version
Company version
Requirement version
Policy version
Rule-engine version
```

This prevents inconsistent evaluations caused by data changing during execution.

---

# 35. Eligibility Replay

The system shall be capable of reconstructing a historical decision.

Example:

> "Why was Student STU001 considered eligible for IBM on September 12, 2026?"

The system shall reconstruct:

```text
Student state
Company requirement state
Policy version
Rule version
Offer state
Dream declaration
Criteria outcomes
Evidence
```

---

# 36. Eligibility Immutability

Completed eligibility evaluations shall be immutable.

Corrections create a new evaluation.

Historical decisions must not be silently rewritten.

---

# 37. AI Agent

The platform shall contain one primary student-aware AI Agent.

The initial architecture shall intentionally avoid a multi-agent system.

The Agent shall orchestrate:

```text
Query
 ↓
Intent
 ↓
Context
 ↓
Tools
 ↓
Eligibility Engine
 ↓
Evidence
 ↓
Explanation
```

---

# 38. Agent Responsibilities

The Agent may:

* Understand natural-language questions.
* Identify company names.
* Identify requested operations.
* Retrieve student context.
* Retrieve company requirements.
* Retrieve policy evidence.
* Invoke eligibility tools.
* Explain results.
* Answer policy questions.
* Present eligible opportunities.
* Request clarification when necessary.

---

# 39. Agent Restrictions

The Agent shall not:

* Directly access PostgreSQL.
* Directly execute SQL.
* Directly modify eligibility results.
* Modify policy rules.
* Activate policies.
* Modify company requirements without authorization.
* Create dream declarations without explicit authorization.
* Invent missing information.
* Treat retrieved text as executable instructions.

---

# 40. Agent Tool Registry

The Agent shall use a controlled tool registry.

Initial tools:

```text
get_student_profile
get_student_academics
get_student_placement_history
get_student_dream_companies

get_company
get_placement_opportunity
get_company_requirements

search_policy
get_policy_evidence
get_active_policy

evaluate_academic_rules
evaluate_package_rule
evaluate_placement_policy
evaluate_eligibility

get_eligibility_history
```

Mutating tools shall be separately authorized.

---

# 41. Tool Authorization

Every tool call shall be checked against:

```text
Authenticated User
+
Role
+
Institution
+
Resource Ownership
+
Tool Permission
```

The LLM itself does not determine authorization.

---

# 42. Agent Workflow — Eligibility

For:

> "Am I eligible for IBM?"

the Agent shall follow approximately:

```text
1. Identify student
2. Identify opportunity
3. Retrieve student facts
4. Retrieve placement history
5. Retrieve company requirements
6. Retrieve applicable policy
7. Invoke eligibility engine
8. Receive deterministic result
9. Retrieve evidence
10. Generate explanation
11. Validate response
12. Return result
```

---

# 43. Agent Workflow — Policy Question

For:

> "Can I attend a company offering the same package as my current offer?"

the Agent shall:

```text
Identify question
      ↓
Retrieve applicable policy
      ↓
Determine relevant rule
      ↓
Return policy-grounded answer
```

If student-specific information is required, it shall retrieve the relevant student context.

---

# 44. Agent Context

The Agent may maintain authorized conversation context.

However:

> **Conversation history shall never be treated as authoritative current eligibility state.**

For a new eligibility request, current data and current applicable policy must be reevaluated.

---

# 45. Agent Output Validation

AI responses shall be schema-validated.

The response should contain:

```text
decision
summary
criteria
blockers
evidence
warnings
```

The backend shall validate that the generated decision matches the deterministic engine result.

---

# 46. AI Abstention

The Agent shall abstain or return an appropriate uncertainty response when:

* Required evidence is missing.
* Policy is ambiguous.
* Data is incomplete.
* Tool calls fail.
* Conflicting information exists.
* LLM output cannot be validated.

Example:

> "I cannot determine your eligibility reliably because the applicable placement policy could not be verified."

---

# 47. OpenAI Dependency

The eligibility engine shall function without OpenAI.

OpenAI is an explanation/orchestration dependency, not a business-rule dependency.

If OpenAI is unavailable:

```text
Deterministic Eligibility
        ↓
Structured Result
```

shall remain available.

---

# 48. Qdrant Dependency

The deterministic eligibility engine shall not require Qdrant for rules that have already been approved and structured.

Qdrant is primarily responsible for:

```text
Policy retrieval
Evidence retrieval
Policy question answering
```

If retrieval is required to establish an unknown policy condition, the decision may become:

```text
UNKNOWN
```

---

# 49. AI and RAG Grounding

AI responses shall be grounded in:

```text
Verified Student Facts
+
Company Requirements
+
Eligibility Results
+
Approved Policy Evidence
```

The Agent shall not cite unsupported policies.

---

# 50. Skill Provenance

Skills may be stored with provenance.

Example:

```text
Skill: Python
Source: Student profile
Verification: Self-declared
```

The system shall distinguish between:

```text
Verified
Self-declared
Imported
Unverified
```

The AI shall not make unsupported claims such as:

> "The student is an expert in Python."

unless such proficiency is explicitly recorded and authorized.

---

# 51. Unrecorded Requirements

If a company mentions a requirement that is not represented in the structured model:

```text
Requirement:
"Strong communication skills"
```

the system shall not automatically transform this into:

```text
communication_score >= 8
```

without an approved rule definition.

Such requirements may be surfaced as:

```text
UNSTRUCTURED_REQUIREMENT
```

and may require review.

---

# 52. Eligible Opportunity Recommendations

The system may recommend opportunities only from opportunities for which eligibility has been deterministically evaluated.

The recommendation engine shall not recommend:

```text
Unknown
```

opportunities as if they were eligible.

Ordering shall be deterministic.

Example ordering:

```text
Eligibility
→ Dream company preference
→ Package
→ Drive date
```

The exact ordering shall be defined by the release contract.

---

# 53. Preparation Plans

Where enabled, the system may provide preparation plans.

The plan may be available for:

```text
Eligible
Not Eligible
Unknown
```

Preparation must not change the eligibility decision.

For example:

```text
NOT_ELIGIBLE

Reason:
CGPA requirement not satisfied.

Preparation:
This opportunity cannot currently be attended.
You may review future opportunities with a lower
CGPA threshold.
```

---

# 54. Administrative Override

Authorized administrators may apply an override where institutional policy permits.

An override shall:

* Preserve the original deterministic result.
* Record the administrator.
* Record the reason.
* Record supporting evidence.
* Record timestamp.
* Record scope.
* Never delete the original evaluation.

Example:

```text
Deterministic Result:
NOT_ELIGIBLE

Administrative Decision:
OVERRIDE → ELIGIBLE

Reason:
Approved institutional exception
```

The UI must clearly distinguish:

```text
Deterministic Result
```

from:

```text
Administrative Override
```

---

# 55. Audit Requirements

The system shall maintain audit logs for:

* Student data changes
* Company changes
* Requirement changes
* Policy lifecycle events
* Document uploads
* Policy activation
* Dream-company declarations
* Eligibility evaluations
* Agent tool calls
* Administrative overrides
* Authentication events
* Authorization failures

---

# 56. Audit Record

An eligibility audit record should contain:

```text
decision_id
student_id
opportunity_id
request_id
timestamp
student_snapshot
requirement_version
policy_version
rule_engine_version
criteria_results
decision
policy_evidence
agent_session_id
```

---

# 57. Decision Provenance

Every decision must answer:

```text
Who?
What student?

For what?
Which company/opportunity?

When?
At what time?

Using what?
Which data versions?

Under what policy?
Which policy version?

Using which engine?
Which rule-engine version?

Why?
Which criteria produced the result?

Evidence?
Which policy sources support the decision?
```

---

# 58. Database

PostgreSQL shall be the authoritative relational database.

Initial entities:

```text
institutions
users
roles

students
student_academic_records
student_semester_records
student_backlogs
student_skills
student_certifications

companies
company_roles
placement_opportunities
company_requirements
company_requirement_versions

student_offers
student_offer_events
student_dream_companies

policies
policy_versions
policy_rules
policy_documents
policy_source_locators

eligibility_checks
eligibility_snapshots
eligibility_criteria_results
eligibility_evidence

agent_sessions
agent_messages
agent_tool_calls

administrative_overrides
audit_logs
```

---

# 59. Database Rules

The database shall enforce:

* Foreign keys
* Unique constraints
* Referential integrity
* Appropriate NOT NULL constraints
* Appropriate check constraints
* Transaction integrity
* Version consistency

---

# 60. API Architecture

FastAPI shall expose versioned REST APIs.

Base path:

```text
/api/v1
```

Primary modules:

```text
/auth
/students
/companies
/opportunities
/requirements
/policies
/documents
/rag
/eligibility
/agent
/audit
/admin
```

---

# 61. Eligibility API

Example:

```http
POST /api/v1/eligibility/check
```

Request:

```json
{
  "student_id": "STU001",
  "opportunity_id": "IBM-SE-2026"
}
```

Response:

```json
{
  "decision_id": "DEC-10001",
  "decision": "ELIGIBLE",
  "student_id": "STU001",
  "opportunity_id": "IBM-SE-2026",
  "criteria": [],
  "evidence": [],
  "evaluated_at": "2026-09-12T10:30:00Z"
}
```

---

# 62. Agent API

Example:

```http
POST /api/v1/agent/chat
```

The API shall authenticate the user and establish the student's authorized context.

The Agent shall operate only through permitted tools.

---

# 63. Authentication

The initial implementation shall support:

```text
JWT
OAuth2-compatible architecture
RBAC
```

Future institutional SSO may use:

```text
OIDC
SAML
```

where required.

---

# 64. Authorization

Authorization must be enforced server-side.

Students shall not access another student's information by modifying request parameters.

Example:

```text
Student A
GET /students/STU002
```

must be rejected unless explicitly authorized.

---

# 65. Security Requirements

The platform shall implement:

* TLS
* Secure authentication
* RBAC
* Input validation
* File validation
* Rate limiting
* Secure secrets
* Security headers
* CORS controls
* SQL injection protection
* Audit logging
* Access logging
* Sensitive-data redaction

---

# 66. Student Privacy

The platform shall minimize student information sent to external AI services.

Only information required to answer the request shall be provided.

Logs shall not contain unnecessary:

```text
Phone numbers
Personal addresses
Authentication credentials
API keys
Sensitive personal information
```

---

# 67. Prompt Injection Defense

Policy documents, user messages, company descriptions, and retrieved content shall be considered untrusted input.

The system shall maintain clear boundaries between:

```text
System Instructions
Tool Definitions
User Input
Student Data
Company Data
Policy Evidence
```

Retrieved policy text shall never gain authority to redefine the Agent's instructions.

---

# 68. File Upload Security

Uploads shall enforce:

* Allowed MIME types
* File extensions
* Maximum file size
* File integrity
* Secure storage
* Malware scanning where available
* Path traversal protection
* Safe parser configuration

---

# 69. Docker Architecture

The application shall be containerized.

Initial services:

```text
frontend
backend
worker
postgres
redis
qdrant
nginx
```

---

# 70. Frontend

Technology:

```text
Next.js
TypeScript
App Router
```

The frontend shall communicate with FastAPI through authenticated APIs.

The frontend shall not contain authoritative business rules.

---

# 71. Backend

Technology:

```text
Python
FastAPI
Pydantic
SQLAlchemy
Alembic
```

The backend shall contain:

```text
API
Application Services
Domain
Eligibility Engine
Policy Services
RAG Services
Agent
Repositories
Workers
```

---

# 72. Backend Architecture

Recommended:

```text
API
 ↓
Application Service
 ↓
Domain
 ↓
Repository
 ↓
Infrastructure
```

Business rules shall remain independent of HTTP and LLM implementations.

---

# 73. AI Agent Architecture

Recommended:

```text
Agent
 ├── Intent
 ├── State
 ├── Tool Registry
 ├── Guardrails
 ├── Policy Context
 └── Response Validation
```

The Agent shall invoke application-level tools.

---

# 74. RAG Architecture

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

Query:

```text
User Query
 ↓
Query Understanding
 ↓
Metadata Filtering
 ↓
Vector Retrieval
 ↓
Optional Reranking
 ↓
Evidence
```

---

# 75. Redis

Redis may provide:

* Caching
* Background job queues
* Rate limiting
* Temporary Agent state
* Document processing state

Redis shall not become the authoritative source for student or policy data.

---

# 76. Background Workers

Workers shall process:

* Document ingestion
* PDF parsing
* Chunking
* Embedding
* Qdrant indexing
* Bulk student imports
* Bulk eligibility calculations

---

# 77. Observability

The system shall provide:

```text
Structured logs
Metrics
Health checks
Request IDs
Agent traces
Tool execution traces
Eligibility traces
```

---

# 78. Health Checks

The backend shall expose:

```text
GET /health
GET /ready
```

Readiness shall validate critical dependencies.

---

# 79. Configuration

Environment configuration shall include:

```env
APP_ENV=
DATABASE_URL=
REDIS_URL=
QDRANT_URL=
OPENAI_API_KEY=
JWT_SECRET=
NEXT_PUBLIC_API_URL=
```

Secrets must never be committed to source control.

---

# 80. Performance Requirements

Initial engineering targets:

```text
Normal API request: < 500 ms
Deterministic eligibility evaluation: < 1 second
Policy retrieval: < 3 seconds
Agent response: < 10 seconds
```

Production measurements shall be based on defined workloads rather than averages from individual requests.

---

# 81. Scalability

The system should initially support:

```text
10,000+ students
1,000+ opportunities
100+ policy documents
Large policy vector collections
Concurrent eligibility requests
```

The backend should remain horizontally scalable.

---

# 82. Reliability

The same input snapshot and rule version must produce the same deterministic result.

Example:

```text
Student Snapshot: S12
Requirement Version: R4
Policy Version: P2026.1
Rule Engine: 1.0
```

must always produce the same deterministic decision.

---

# 83. Testing Strategy

Testing shall include:

```text
Unit
Integration
API
Database
Eligibility
Policy
RAG
Agent
Security
E2E
Performance
Recovery
```

---

# 84. Eligibility Test Matrix

At minimum:

```text
SSLC exactly equal threshold
SSLC below threshold
SSLC above threshold

HSC exactly equal threshold
HSC below threshold
HSC above threshold

CGPA exactly equal threshold
CGPA below threshold
CGPA above threshold

Backlog boundary
Degree mismatch
Department mismatch
Graduation-year mismatch
```

---

# 85. Package Test Matrix

Given:

```text
Previous Offer = ₹5 LPA
```

test:

```text
₹3 LPA → NOT_ELIGIBLE
₹4 LPA → NOT_ELIGIBLE
₹5 LPA → NOT_ELIGIBLE
₹6 LPA → ELIGIBLE
```

For authorized dream company:

```text
₹3 LPA → NOT_ELIGIBLE
₹4 LPA → NOT_ELIGIBLE
₹5 LPA → ELIGIBLE
₹6 LPA → ELIGIBLE
```

provided all other requirements pass.

---

# 86. Unknown-State Tests

The system shall verify:

```text
Missing CGPA
Missing company requirement
Missing policy
Conflicting policy
Unavailable RAG
Invalid policy version
```

produce a safe non-definitive state rather than a guessed decision.

---

# 87. Agent Testing

Agent tests shall verify:

* Intent recognition
* Company identification
* Correct student context
* Correct tool selection
* Correct authorization
* Correct policy retrieval
* Correct eligibility invocation
* Correct response grounding
* No hallucinated criteria
* No unauthorized mutation
* No eligibility override

---

# 88. RAG Evaluation

RAG quality shall be measured using a controlled evaluation set.

Metrics may include:

```text
Retrieval precision
Retrieval recall
Evidence relevance
Policy-version accuracy
Citation/source accuracy
Abstention accuracy
```

RAG quality must not be assumed from successful vector search alone.

---

# 89. End-to-End Acceptance Test

Student:

```text
SSLC = 75%
HSC = 70%
CGPA = 7.5
Backlogs = 0
Previous Accepted Offer = ₹5 LPA
Dream Company = IBM
```

IBM:

```text
SSLC >= 70%
HSC >= 65%
CGPA >= 7.0
Backlogs = 0
Package = ₹5 LPA
```

Active policy:

```text
Equal package permitted for authorized dream company.
```

Expected:

```text
ELIGIBLE
```

---

# 90. Normal Company Acceptance Test

Same student:

```text
Previous Offer = ₹5 LPA
```

Company:

```text
Package = ₹5 LPA
Dream Company = false
```

Expected:

```text
NOT_ELIGIBLE
```

Reason:

```text
Equal package is not permitted for a normal opportunity.
```

---

# 91. Policy Unavailable Test

If an eligibility condition depends on a policy that cannot be verified:

Expected:

```text
UNKNOWN
```

The system shall not claim:

```text
ELIGIBLE
```

or:

```text
NOT_ELIGIBLE
```

without sufficient evidence.

---

# 92. Release Structure

## R0 — Foundation

Deliver:

```text
Repository
Docker
Next.js
FastAPI
PostgreSQL
Redis
Qdrant
Authentication foundation
CI
Configuration
Logging
```

---

## R1 — Deterministic Decision MVP

Deliver:

```text
Student data
Company data
Requirements
Policy definitions
Policy lifecycle
Placement history
Package rules
Dream-company exception
Eligibility Engine
Decision API
Audit
Replay
```

R1 is the first production-capable decision foundation.

---

# 93. R2 — Policy Intelligence

Deliver:

```text
PDF ingestion
Markdown ingestion
TXT ingestion
Document preservation
Embeddings
Qdrant
Policy retrieval
Evidence
Policy Q&A
Validated AI explanations
AI outage fallback
```

---

# 94. R3 — AI Placement Copilot

Deliver:

```text
Student-aware Agent
Tool registry
Natural-language eligibility
Policy questions
Eligible-company discovery
Conversation context
Preparation assistance
Grounded explanations
```

---

# 95. R4 — Administrative Intelligence

Deliver:

```text
Administrative overrides
Advanced analytics
Institutional reporting
Advanced audit
Operational dashboards
```

---

# 96. Release Gates

A release shall not be considered complete merely because implementation exists.

Each release requires:

```text
Requirements
+
Implementation
+
Automated Tests
+
Security Validation
+
Evidence
+
Operational Validation
+
Acceptance Report
```

---

# 97. R1 Release Gate

R1 requires successful validation of:

```text
Student data
Company requirements
Policy definitions
Offer selection
Package rules
Dream exceptions
Eligibility aggregation
Unknown state
Audit
Replay
API
Security
```

---

# 98. R2 Release Gate

R2 additionally requires:

```text
Document ingestion
Document provenance
Policy retrieval
Version filtering
Evidence
RAG evaluation
AI explanation validation
AI outage behavior
```

---

# 99. R3 Release Gate

R3 additionally requires:

```text
Agent tool authorization
Agent evaluation
Prompt-injection tests
Conversation handling
Tool traces
Grounded response tests
Eligibility consistency
```

---

# 100. Production Readiness

Production deployment requires:

```text
Docker images
Secure environment variables
TLS
Database backup
Restore validation
Qdrant backup
Health checks
Monitoring
Logging
Security validation
Rate limiting
Data retention
Incident procedures
```

---

# 101. Backup and Recovery

PostgreSQL shall have scheduled backups.

Recovery procedures shall be tested rather than merely documented.

The system shall define:

```text
RPO
RTO
Backup retention
Restore procedure
Disaster recovery owner
```

---

# 102. Data Retention

Institution-approved retention periods shall be configured for:

```text
Student data
Eligibility decisions
Agent conversations
Audit records
Policy documents
Policy versions
System logs
```

Historical eligibility evidence required for institutional audit must not be deleted before its approved retention period.

---

# 103. Decision Explainability

The UI shall present:

```text
Final Decision
+
Compared Values
+
Passed Criteria
+
Failed Criteria
+
Unknown Criteria
+
Applicable Policy
+
Evidence
+
Evaluation Time
```

---

# 104. Non-AI Decision UI

Eligibility results must remain understandable even without AI-generated prose.

Example:

```text
Decision: NOT_ELIGIBLE

CGPA
Student: 6.8
Required: 7.0
Result: FAIL

Package
Previous: ₹5 LPA
Company: ₹5 LPA
Dream Company: No
Result: FAIL
```

---

# 105. AI Explanation UI

AI-generated explanations shall supplement, not replace, the structured decision.

The user must be able to see the underlying deterministic result.

---

# 106. Auditability Requirement

For every student/company evaluation, the system must be capable of answering:

> Why?

The answer must be derived from recorded facts and evidence rather than reconstructing an explanation from memory.

---

# 107. Security Boundary

The following boundaries are mandatory:

```text
Frontend
    ↓
Authenticated API
    ↓
Application Services
    ↓
Domain / Eligibility
    ↓
Repositories
    ↓
PostgreSQL
```

and:

```text
Agent
    ↓
Authorized Tools
    ↓
Application Services
```

The Agent must not bypass these boundaries.

---

# 108. AI Provider Independence

The domain and eligibility engine shall not depend directly on OpenAI SDK semantics.

The architecture should allow future support for:

```text
OpenAI
Local LLM
Other compatible providers
```

without rewriting the eligibility engine.

---

# 109. Vector Provider Independence

RAG interfaces should abstract Qdrant behind a retrieval service.

Future vector stores may be supported without changing business rules.

---

# 110. Business Rule Versioning

The eligibility engine shall be versioned.

Example:

```text
Rule Engine 1.0
Rule Engine 1.1
```

Every historical decision shall record the engine version.

---

# 111. API Versioning

API endpoints shall use:

```text
/api/v1
```

Breaking API changes require a new version.

---

# 112. Error Model

The API shall return structured errors.

Examples:

```text
STUDENT_NOT_FOUND
OPPORTUNITY_NOT_FOUND
REQUIREMENT_INCOMPLETE
POLICY_NOT_FOUND
POLICY_CONFLICT
UNAUTHORIZED
FORBIDDEN
VALIDATION_ERROR
DEPENDENCY_UNAVAILABLE
ELIGIBILITY_UNKNOWN
```

---

# 113. Logging Requirements

Logs shall contain sufficient operational information to debug requests while avoiding unnecessary student PII.

Each request should have:

```text
request_id
trace_id
service
timestamp
status
latency
```

---

# 114. Project Repository

Recommended structure:

```text
ai-placement-intelligence/
│
├── apps/
│   ├── web/
│   └── api/
│
├── packages/
│   └── shared/
│
├── infrastructure/
│   ├── docker/
│   ├── nginx/
│   └── scripts/
│
├── docs/
│   ├── srs/
│   ├── architecture/
│   ├── contracts/
│   ├── policies/
│   └── operations/
│
├── tests/
│   ├── e2e/
│   └── evaluation/
│
├── docker-compose.yml
├── .env.example
├── Makefile
└── README.md
```

---

# 115. Recommended Backend Structure

```text
apps/api/
│
├── app/
│   ├── api/
│   ├── core/
│   ├── domain/
│   ├── application/
│   ├── repositories/
│   ├── eligibility/
│   ├── policies/
│   ├── rag/
│   ├── agents/
│   ├── tools/
│   ├── workers/
│   └── infrastructure/
│
└── tests/
```

---

# 116. Recommended Frontend Structure

```text
apps/web/
│
├── app/
│   ├── login/
│   ├── dashboard/
│   ├── profile/
│   ├── companies/
│   ├── eligibility/
│   ├── assistant/
│   └── admin/
│
├── components/
├── lib/
├── hooks/
└── types/
```

---

# 117. Definition of Done

A requirement shall be considered complete only when:

```text
Requirement implemented
        +
Unit tests
        +
Integration tests
        +
Negative tests
        +
Security validation
        +
Observability
        +
Documentation
        +
Acceptance evidence
```

Code existence alone shall not constitute completion.

---

# 118. Engineering Quality Principles

The project shall follow:

### Determinism

Eligibility must be reproducible.

### Explainability

The system must show why.

### Provenance

Every important fact and rule must have a source.

### Versioning

Policy and requirements must be versioned.

### Immutability

Historical decisions must remain intact.

### Least Privilege

Agent and users receive only required access.

### Fail Safe

Uncertainty must not become false certainty.

### AI as Assistant

AI orchestrates and explains.

### Policy as Authority

Approved institutional policy controls business decisions.

### Evidence over Claims

Every policy-backed decision must have evidence.

---

# 119. Core Product Workflow

The final product workflow shall be:

```text
                    Student
                       │
                       ▼
                 Natural Language
                       │
                       ▼
                ┌───────────────┐
                │   AI Agent    │
                └───────┬───────┘
                        │
               Authorized Tools
                        │
       ┌────────────────┼────────────────┐
       │                │                │
       ▼                ▼                ▼
   Student DB      Company DB       Policy RAG
       │                │                │
       └────────────────┼────────────────┘
                        │
                        ▼
             ┌─────────────────────┐
             │ Eligibility Engine   │
             │                     │
             │ Deterministic Rules │
             └──────────┬──────────┘
                        │
                        ▼
             ┌─────────────────────┐
             │ Verified Decision   │
             │                     │
             │ ELIGIBLE            │
             │ NOT_ELIGIBLE        │
             │ UNKNOWN             │
             └──────────┬──────────┘
                        │
                        ▼
             Policy Evidence + Facts
                        │
                        ▼
                 AI Explanation
                        │
                        ▼
                  Student UI
```

---

# 120. Final Product Guarantee

The platform shall guarantee the following architectural behavior:

> **A student eligibility decision is generated from authoritative student data, applicable company requirements, approved placement policies, placement history, and explicitly authorized exceptions through a deterministic eligibility engine.**

> **The AI Agent may orchestrate retrieval and tools and may explain the resulting decision, but it cannot independently create, modify, or override eligibility rules or deterministic decisions.**

> **Policy RAG provides evidence and knowledge retrieval but does not directly create executable rules.**

> **Historical decisions remain reproducible through immutable snapshots, policy versions, requirement versions, and engine versions.**

> **When required information cannot be verified, the system returns UNKNOWN rather than guessing.**

---

# 121. Final Scope Statement

The AI-Powered Student Placement Intelligence Platform is a:

> **Web-based, policy-grounded student placement decision-support platform that combines verified student information, versioned company requirements, approved institutional placement policies, deterministic eligibility evaluation, policy RAG, and a controlled AI Agent to provide explainable, auditable, and reproducible placement eligibility decisions.**

The core product is:

```text
STUDENT
   ↓
COMPANY / OPPORTUNITY
   ↓
REQUIREMENTS
   ↓
PLACEMENT POLICY
   ↓
PLACEMENT HISTORY
   ↓
AUTHORIZED EXCEPTIONS
   ↓
DETERMINISTIC ELIGIBILITY
   ↓
POLICY EVIDENCE
   ↓
AI EXPLANATION
```

The core decision states are:

```text
ELIGIBLE
NOT_ELIGIBLE
UNKNOWN
```

The system shall prioritize:

```text
Correctness
>
Auditability
>
Policy Compliance
>
Security
>
Explainability
>
AI Convenience
```

This ordering is mandatory for production decision-making.
