# Requirements That Must Be Contracted Before Implementation

The SRS intentionally delegates several details to separate normative contracts. Do not invent these details in code.

## Required contracts

1. Domain Model
2. Business Rules
3. Policy Lifecycle
4. Eligibility Contract
5. Agent Contract
6. RAG Contract
7. Security Contract
8. Release Scope
9. Roadmap

## Highest-priority unresolved implementation contracts

### Eligibility aggregation
The SRS says the exact aggregation rules are defined in the Eligibility Contract.

Define:
- mandatory vs optional criteria behavior
- interaction between FAIL and UNKNOWN
- NOT_APPLICABLE semantics
- policy conflicts
- exception ordering
- administrative override semantics

### Offer selection
The SRS requires policy-defined selection and gives "highest accepted offer" as an example. The authoritative selection algorithm must be specified.

### Package rules
Define the exact policy inputs and precedence for:
- normal company
- dream company
- accepted/rejected/withdrawn/expired offers
- multiple applicable offers

### Requirement completeness
Define how Required, Not Applicable, Optional, and Unknown are represented and evaluated.

### Policy conflict
Define when conflicting active definitions cause UNKNOWN, REVIEW_REQUIRED, or an administrative block.

### RAG contract
Define:
- chunking policy
- embedding model/interface
- metadata schema
- retrieval filters
- ranking/reranking
- evidence minimums
- citation format
- historical retrieval behavior

### Agent contract
Define:
- tool schemas
- authorization checks
- tool result schemas
- response schema
- validation rules
- mutation confirmation/authorization model
- context/session rules

### Release contract
Define exact R0-R4 acceptance criteria and evidence artifacts.

Do not silently resolve these gaps from model knowledge.
