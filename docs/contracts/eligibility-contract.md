# Eligibility contract draft

Primary decisions: ELIGIBLE, NOT_ELIGIBLE, UNKNOWN.
Criterion states: PASS, FAIL, UNKNOWN, NOT_APPLICABLE.
REVIEW_REQUIRED, if used, is a review workflow state and not a fourth decision.

Inputs: one consistent student/academic/offer/dream/opportunity/requirement/policy
snapshot, including versions, evaluation instant and rule-engine version.
Outputs: decision, compared values, operators, criterion outcomes, source locators,
selected offer, applied exceptions, timestamps and immutable decision ID.

Rules are pure domain code without HTTP, SQL, vector or LLM dependencies. All
criteria are evaluated for useful reasons rather than stopping at the first failure.
Aggregation precedence remains a proposed interpretation in release-scope.md.

Completed evaluations and snapshots are immutable. Replay must use saved facts,
definitions and supported engine version, never today's data. Current API identity
and resource authorization must be checked before evaluating or replaying a record.
Retrieval outages do not change a decision backed by complete approved rules.
