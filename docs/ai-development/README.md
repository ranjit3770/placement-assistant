# AI Development Configuration

This directory documents how Codex and Antigravity should be used on this project.

## Source of truth

`docs/srs/` contains the authoritative SRS.

## Tool roles

### Codex
Use Codex primarily for:
- repository inspection
- implementation
- refactoring
- debugging
- test creation
- running verification
- applying fixes from reviews

Codex should follow the repository `AGENTS.md`.

### Antigravity
Use Antigravity primarily for:
- architecture exploration
- specialized parallel reviews
- research within the repository
- QA/security/design investigations
- browser/UI verification where appropriate
- delegating focused work to custom agents

Antigravity workspace customizations live under `.agents/`.

## Rule

Do not create competing business-rule implementations in agent instructions.

Agent files describe responsibilities and execution boundaries. The SRS and implementation contracts define product behavior.

## Recommended workflow

1. Read the relevant SRS section.
2. Read applicable contract.
3. Architect or investigate if the change is broad.
4. Implement with Codex.
5. Run focused tests.
6. Review with QA/security agents where applicable.
7. Fix findings.
8. Run release-gate verification.
9. Record acceptance evidence.
