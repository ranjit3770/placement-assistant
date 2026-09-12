# Business rules contract draft

Company criteria and institutional policy are explicit, approved definitions.
Supported comparisons: >, >=, <, <=, =, !=, IN, NOT_IN, BETWEEN.
Missing requirements never imply no restriction. No implicit grade conversion.

For the documented package policy: a new normal-company package must exceed
the applicable previous offer. An equal package passes only for an authorized,
policy-backed dream-company exception. A lower package fails even for a dream
company. All unrelated mandatory criteria must still pass.

Policy defines which offers count, selection strategy, dream declaration/approval
cutoffs and permitted companies. A query never mutates declarations. Unresolved
policy semantics produce UNKNOWN; the engine cannot supply invented defaults.
See release-scope.md for decisions required before implementing these rules.

The coordinator confirmed the initial M2 baseline on 2026-09-12:

- Highest valid accepted offer applicable to the current placement context;
  no qualifying offer means absent previous package.
- One explicitly declared and authorized approved dream company per academic year,
  with declaration/approval before announcement and no student changes afterward.
- Exact annual total CTC in INR; display LPA. Non-comparable or ambiguous terms
  remain unresolved, never silently converted into an eligibility input.

These are domain decisions, not automatic institutional policy activation.
See [M2 decision register](m2-decisions.md) for details and versioning boundaries.
