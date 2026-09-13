---
name: rag
description: Implements policy document ingestion, metadata-aware Qdrant retrieval, evidence traceability, and RAG evaluation.
---

# RAG Skill

Pipeline:
Document -> Parser -> Normalizer -> Chunker -> Metadata -> Embedding -> Qdrant

Retrieval must prioritize:
1. active policy
2. applicable academic year
3. applicable institution
4. applicable scope
5. relevant section
6. company-specific policy where applicable

Historical documents must not override active policy unless historical evaluation is explicitly requested.

Preserve evidence and source references.

If required evidence cannot be verified, do not fabricate an answer; allow the application to produce UNKNOWN or the contract-defined non-definitive state.

Qdrant is a retrieval dependency, not the authoritative business-rule store.
