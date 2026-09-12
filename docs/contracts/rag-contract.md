# RAG contract draft (M6)

Preserve originals → parse → normalize → chunk → embed → index in Qdrant.
Each stage has an interface and retry/idempotency strategy. Hashes prevent duplicate
ingestion. Metadata binds institution, policy/version, year, document, page/section,
chunk and source hash. Filter authorization before retrieval, not after generation.

Evidence must resolve to preserved authorized source content. Active applicable
policy outranks historical material for current questions. No fabricated citations.
Evaluation uses fixed questions with expected versions/locators and abstention cases.
Qdrant and OpenAI are replaceable adapters, never rule authorities.
