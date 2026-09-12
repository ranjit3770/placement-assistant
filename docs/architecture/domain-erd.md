# M2 Domain ERD

Design draft, not an applied schema. See [domain model](../contracts/domain-model.md)
and [confirmed decisions](../contracts/m2-decisions.md). All private relationships
also include institution_id in their physical foreign keys. Reference and event
tables are detailed in the domain model even where omitted here for readability.

## Identity and academics

```mermaid
erDiagram
    INSTITUTIONS ||--o{ ACADEMIC_YEARS : defines
    INSTITUTIONS ||--o{ USERS : owns
    INSTITUTIONS ||--o{ STUDENTS : owns
    USERS ||--o{ USER_ROLES : receives
    ROLES ||--o{ USER_ROLES : grants
    USERS o|--o| STUDENTS : authenticates
    STUDENTS ||--|{ STUDENT_REVISIONS : records
    STUDENTS ||--o{ STUDENT_ACADEMIC_RECORDS : revises
    STUDENT_ACADEMIC_RECORDS ||--o{ STUDENT_SEMESTER_RECORDS : contains
    GRADING_SCALES ||--o{ STUDENT_SEMESTER_RECORDS : measures
    STUDENTS ||--o{ STUDENT_BACKLOGS : owes
    STUDENT_BACKLOGS ||--|{ STUDENT_BACKLOG_EVENTS : tracks
    STUDENTS ||--o{ STUDENT_SKILLS : records
    STUDENTS ||--o{ STUDENT_CERTIFICATIONS : records
```

## Recruitment and placement history

```mermaid
erDiagram
    COMPANIES ||--o{ COMPANY_ROLES : offers
    COMPANIES ||--o{ PLACEMENT_DRIVES : attends
    ACADEMIC_YEARS ||--o{ PLACEMENT_DRIVES : groups
    PLACEMENT_DRIVES ||--o{ PLACEMENT_OPPORTUNITIES : contains
    COMPANY_ROLES ||--o{ PLACEMENT_OPPORTUNITIES : recruits
    PLACEMENT_OPPORTUNITIES ||--o| COMPANY_REQUIREMENTS : defines
    COMPANY_REQUIREMENTS ||--o{ COMPANY_REQUIREMENT_VERSIONS : versions
    COMPANY_REQUIREMENT_VERSIONS ||--o{ REQUIREMENT_CRITERIA : contains
    COMPENSATION_TERMS ||--o{ COMPANY_REQUIREMENT_VERSIONS : describes
    STUDENTS ||--o{ STUDENT_OFFERS : receives
    COMPANIES ||--o{ STUDENT_OFFERS : makes
    PLACEMENT_OPPORTUNITIES o|--o{ STUDENT_OFFERS : originates
    STUDENT_OFFERS ||--|{ STUDENT_OFFER_EVENTS : records
    COMPENSATION_TERMS o|--o{ STUDENT_OFFER_EVENTS : describes
    STUDENTS ||--o{ STUDENT_DREAM_COMPANIES : declares
    COMPANIES ||--o{ STUDENT_DREAM_COMPANIES : identifies
    ACADEMIC_YEARS ||--o{ STUDENT_DREAM_COMPANIES : scopes
    STUDENT_DREAM_COMPANIES ||--|{ DREAM_DECLARATION_EVENTS : records
    DREAM_DECLARATION_EVENTS ||--o{ DREAM_DRIVE_LOCKS : freezes
    PLACEMENT_DRIVES ||--o{ DREAM_DRIVE_LOCKS : locks
```

Imported external offers may lack a campus opportunity. Multiple declaration rows
preserve history; initial simultaneous approved cardinality is one. An opportunity's
role and drive must belong to the same company. Locks preserve original cutoffs.

## Policies and decisions

```mermaid
erDiagram
    INSTITUTIONS ||--o{ POLICIES : governs
    POLICIES ||--o{ POLICY_VERSIONS : versions
    POLICY_VERSIONS ||--o{ POLICY_RULES : defines
    POLICY_VERSIONS ||--o{ POLICY_LIFECYCLE_EVENTS : transitions
    POLICY_VERSIONS ||--o{ POLICY_ACTIVATIONS : applies
    POLICY_RULES ||--o{ RULE_SOURCE_LINKS : supported_by
    POLICY_DOCUMENTS ||--o{ POLICY_SOURCE_LOCATORS : locates
    POLICY_SOURCE_LOCATORS ||--o{ RULE_SOURCE_LINKS : supports
    REQUIREMENT_CRITERIA ||--o{ REQUIREMENT_SOURCE_LINKS : supported_by
    POLICY_SOURCE_LOCATORS ||--o{ REQUIREMENT_SOURCE_LINKS : supports
    STUDENTS ||--o{ ELIGIBILITY_CHECKS : evaluated
    PLACEMENT_OPPORTUNITIES ||--o{ ELIGIBILITY_CHECKS : targeted
    ELIGIBILITY_CHECKS ||--|| ELIGIBILITY_SNAPSHOTS : freezes
    ELIGIBILITY_CHECKS ||--o{ ELIGIBILITY_CRITERIA_RESULTS : explains
    ELIGIBILITY_CHECKS ||--o{ ELIGIBILITY_EVIDENCE : preserves
    POLICY_SOURCE_LOCATORS ||--o{ ELIGIBILITY_EVIDENCE : supports
    ELIGIBILITY_CHECKS ||--o{ ADMINISTRATIVE_OVERRIDES : separately_overridden
    INSTITUTIONS ||--o{ AUDIT_LOGS : audits
```

The one-to-one snapshot relationship applies to completed evaluations. Snapshots
freeze values, definitions, versions, offer/declaration history and engine version.
Evidence binds to preserved source originals rather than mutable filename pointers.
