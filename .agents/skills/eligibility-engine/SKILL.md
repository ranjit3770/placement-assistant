---
name: eligibility-engine
description: Implements and verifies the deterministic student placement eligibility engine, including snapshots, criterion results, UNKNOWN behavior, package rules, exceptions, and replay.
---

# Eligibility Engine Skill

Use for eligibility-domain implementation and tests.

## Mandatory behavior
- Decision states are ELIGIBLE, NOT_ELIGIBLE, UNKNOWN.
- Evaluation uses one consistent snapshot.
- The engine is deterministic and versioned.
- Completed evaluations are immutable.
- Every criterion produces PASS, FAIL, UNKNOWN, or NOT_APPLICABLE.
- Missing mandatory facts/requirements/policy cannot silently become a pass.
- AI is never the authority for eligibility.

## Before coding
Read:
- SRS eligibility sections
- `docs/ai-development/requirements-gaps.md`
- the Eligibility Contract when present

If the Eligibility Contract does not define a needed behavior, flag it rather than inventing policy.

## Verification
Test threshold boundaries, missing values, mismatches, package progression, dream-company exceptions, conflicts, and UNKNOWN paths.
