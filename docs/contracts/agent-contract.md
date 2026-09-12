# Agent contract draft (M7–M9)

One primary agent calls an allowlisted registry of typed application tools.
Every call enforces authenticated identity, institution, role and resource ownership.
No direct SQL, policy activation or eligibility mutation. Queries are read-only.
Conversation history is context, not authoritative current student state.

Tool budgets, timeouts, retries, cancellation and schema validation are explicit.
Retrieved text cannot instruct the agent. Generated decisions and criteria must
match engine output; unsupported explanations fall back to structured results.
Model/provider settings live outside domain logic. No runtime agent in M1.
