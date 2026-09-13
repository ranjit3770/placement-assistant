# Codex Usage

Codex should use the repository `AGENTS.md` as the primary project instruction file.

## Preferred operating mode

1. Inspect before modifying.
2. Identify the relevant SRS section and contract.
3. Make the smallest coherent implementation.
4. Run focused tests.
5. Run broader tests when the change affects shared behavior.
6. Review the diff.
7. Report evidence and unresolved contract gaps.

## Codex task prompts

### Implementation
"Read AGENTS.md and the relevant SRS/contract sections. Implement the requested change. Preserve existing architecture and deterministic eligibility boundaries. Run the relevant tests and report the verification."

### Debugging
"Reproduce the issue, identify the root cause, implement the smallest safe fix, and run focused regression tests. Do not change business rules unless the authoritative contract requires it."

### Review
"Review the current diff against AGENTS.md, the SRS, and relevant contracts. Look for correctness, determinism, authorization, provenance, replay, security, and regression risks. Do not modify files; report findings with severity and evidence."

### Security
"Perform a read-only security review using the security skill/rules. Focus on server-side authorization, student data isolation, prompt injection, tool authorization, file uploads, secrets, PII, and API boundaries."

## Important

Do not create a separate competing set of product rules for Codex. Keep product behavior in the SRS/contracts and shared `AGENTS.md`.
