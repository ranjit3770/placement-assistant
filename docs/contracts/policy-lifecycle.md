# Policy lifecycle contract draft

DRAFT → PROCESSING → REVIEW → APPROVED → ACTIVE → ARCHIVED.
Only an authorized actor may approve or activate; activation is transactional.
An active version's rule definition and source bindings cannot be edited.
Corrections create a new version. Lifecycle events preserve actor/time/reason.

Raw documents and extracted candidate rules are untrusted source material.
Human review converts candidates into approved executable definitions. Preserve
document hashes, originals, versions, sections/pages and effective dates.
Conflicting active definitions yield UNKNOWN, not arbitrary selection.
