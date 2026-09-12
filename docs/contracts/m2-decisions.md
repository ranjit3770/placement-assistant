# Confirmed M2 domain decisions

Confirmed by the project coordinator on 2026-09-12. These are initial domain-model
decisions, not a claim that institutional policy is approved or active.

## Applicable accepted offer

Use the highest-value accepted offer that is not revoked, withdrawn or expired
and applies to the student's current placement context. Preserve all offers and
events. No qualifying offer means absent previous accepted package, not zero.
Record context explicitly (institution, academic year and placement scope).
Unknown applicability or compensation on a potentially qualifying offer must not
be silently ignored to select a lower known offer. Equal-value offers use stable
acceptance-time then UUID ordering for provenance, without changing the amount.

## Dream-company declaration

Initially, one approved company per student per academic year. Declaration must
be an explicit student action and pass the authorized approval workflow. Both
declaration and approval must precede the original drive announcement, as confirmed
in the clarification. The comparison is strict: equality at the cutoff is too late.
No student changes after announcement; rescheduling must not reopen the cutoff.
Preserve declaration, approval, change and lock history.

AI and routine eligibility queries cannot create or change a declaration. The
equal-package exception requires explicit authorization from active institutional
policy and affects only package comparison, never academics, department, backlogs
or other company requirements.

## Compensation

Exact annual total CTC in INR is the authoritative comparable amount. Display LPA:
INR 500000 annually → 5.00 LPA. Display rounding does not change comparisons.
Preserve source amount, currency, period, basis, exact/range shape and original text.

Ranges, monthly/hourly amounts, foreign currencies, non-CTC structures, equity-heavy
or ambiguous terms are UNRESOLVED until an authoritative conversion/rule exists.
Never silently annualize, convert currency or choose a range endpoint. A required
unresolved comparison leads to UNKNOWN/review handling; review status is metadata,
not a fourth primary eligibility decision.

## Policy evolution

Do not seed these decisions as ACTIVE policy. Approval/activation belongs to M4.
Selection strategies, dream limits/cutoffs and compensation conversions are
versioned definitions, referenced by snapshots and historical locks. Later approved
policy may supersede the baseline without rewriting facts or past decisions.

Other interpretation details remain explicit for later contracts: SGPA semester
selection, HSC/diploma alternatives, historical backlog metric, cross-scope policy
composition and UNKNOWN/FAIL aggregation precedence.
