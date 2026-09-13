# Agent Matrix

## Primary agents

| Agent | Purpose | Write code | Run commands | Main responsibility |
|---|---|---:|---:|---|
| architect | Architecture and contract analysis | No by default | Limited | Design and dependency analysis |
| backend-engineer | FastAPI/domain/application implementation | Yes | Yes | Backend implementation |
| frontend-engineer | Next.js UI implementation | Yes | Yes | Frontend implementation |
| database-engineer | PostgreSQL/schema/query/migration work | Yes | Yes | Data layer |
| rag-engineer | Policy ingestion/retrieval/evidence | Yes | Yes | RAG pipeline |
| agent-engineer | Controlled AI Agent/tool registry | Yes | Yes | Agent layer |
| qa-engineer | Test design and verification | Yes for tests | Yes | Quality validation |
| security-engineer | Security review | No by default | Yes/read-only | Security validation |
| release-engineer | Production/release validation | Limited | Yes | Release gates |

## Delegation rules

- Architecture questions -> architect
- PostgreSQL schema/query/migration -> database-engineer
- Eligibility engine -> backend-engineer + qa-engineer
- Policy ingestion/RAG -> rag-engineer + qa-engineer
- Agent/tool authorization -> agent-engineer + security-engineer
- UI -> frontend-engineer + qa-engineer
- Security-sensitive changes -> security-engineer review
- Release completion -> release-engineer

## Important

The product itself intentionally starts with one application AI Agent. These development agents are engineering assistants and do not imply a multi-agent runtime architecture in the product.
