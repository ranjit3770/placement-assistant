# Antigravity Usage

Workspace custom agents live under `.agents/agents/` and skills under `.agents/skills/`.

## Recommended usage

Use `architect` for broad design questions.

Use specialized agents for focused work:
- backend-engineer
- frontend-engineer
- database-engineer
- rag-engineer
- agent-engineer
- qa-engineer
- security-engineer
- release-engineer

## Delegation pattern

For a broad feature:
1. architect investigates
2. implementation agent changes code
3. qa-engineer verifies
4. security-engineer reviews security-sensitive changes
5. release-engineer validates the release gate

Keep delegated tasks narrow and independently verifiable.

## Product boundary

These are development agents. The application itself still contains one primary AI Agent as required by the SRS.
