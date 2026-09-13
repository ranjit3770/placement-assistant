# Eligibility contract — certified M5 boundary

The coordinator's independent M5 certification pins
`d75ffbb06a9479e8451a44f82af870864cbfb38b`.
See [certification scope and evidence caveat](../project-status/m5.md).
This status update records the certified semantics; it changes no evaluator code.

Primary decisions: ELIGIBLE, NOT_ELIGIBLE, UNKNOWN.
Criterion states: PASS, FAIL, UNKNOWN, NOT_APPLICABLE.
REVIEW_REQUIRED, if used, is a review workflow state and not a fourth decision.

Inputs: one consistent student/academic/offer/dream/opportunity/requirement/policy
snapshot, including versions, evaluation instant and rule-engine version.
Outputs: decision, compared values, operators, criterion outcomes, source locators,
selected offer, applied exceptions, timestamps and immutable decision ID.

Rules are pure domain code without HTTP, SQL, vector or LLM dependencies. All
criteria are evaluated for useful reasons rather than stopping at the first failure.
Certified aggregation precedence is FAIL > UNKNOWN > PASS: any authoritative
FAIL produces NOT_ELIGIBLE; otherwise any UNKNOWN produces UNKNOWN; otherwise
the evaluator returns ELIGIBLE. This supersedes the earlier UNKNOWN-first proposal.

Policy selection is a distinct precondition: the certified service returns
NO_ACTIVE_POLICY (400) for zero matching policies and POLICY_AMBIGUITY (500) for
multiple matches. These API errors are not silently converted into persisted
eligibility decisions. M6 evidence availability must not change that behavior.

Completed evaluations and snapshots are immutable. Replay must use saved facts,
definitions and supported engine version, never today's data. Current API identity
and resource authorization must be checked before evaluating or replaying a record.
Retrieval outages do not change a decision backed by complete approved rules.
