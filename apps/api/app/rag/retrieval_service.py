import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.rag import (
    RagChunk,
    RagPolicySource,
    RagPublishedGeneration,
    RagIngestionRun,
    RagIndexGeneration,
    RagSourceObject,
)
from app.rag.contracts import (
    CitationMetadata,
    EmbeddingProvider,
    EvidenceError,
    VerifiedEvidence,
)
from app.rag.qdrant_adapter import QdrantAdapter

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(
        self,
        session: AsyncSession,
        provider: EmbeddingProvider,
        qdrant: QdrantAdapter,
    ) -> None:
        self.session = session
        self.provider = provider
        self.qdrant = qdrant

    async def retrieve(
        self,
        institution_id: UUID,
        policy_version_id: UUID,
        query: str,
        limit: int = 5,
    ) -> list[VerifiedEvidence]:
        """Authorized retrieval of verified evidence.

        Enforces tenant isolation and policy version constraints.
        Abstains (returns empty list) if the context is invalid, unauthorized,
        or unpublished. Qdrant is treated as an untrusted index, and all
        results are re-validated against the PostgreSQL source of truth.
        """
        # 1. PostgreSQL Authorization
        generation = await self.session.scalar(
            select(RagPublishedGeneration)
            .join(RagPolicySource, RagPublishedGeneration.binding_id == RagPolicySource.id)
            .where(
                RagPublishedGeneration.institution_id == institution_id,
                RagPolicySource.policy_version_id == policy_version_id,
            )
        )
        if not generation:
            logger.info(
                "No published generation for institution=%s policy_version=%s",
                institution_id,
                policy_version_id,
            )
            return []

        # 2. Vector Generation
        try:
            vectors = await self.provider.embed([query])
            query_vector = vectors[0]
        except Exception as e:
            logger.exception("Failed to embed search query")
            # If embedding fails due to a network error, we raise EvidenceError
            # so the caller knows the service is degraded, not that there is NO evidence.
            raise EvidenceError("EMBEDDING_FAILED") from e

        # 3. Qdrant Search
        space_id = self.provider.space.space_id
        collection_name = f"rag_{institution_id.hex}_{space_id}"
        
        try:
            candidates = await self.qdrant.search(
                collection_name=collection_name,
                query_vector=query_vector,
                limit=limit,
                generation_id=generation.generation_id,
            )
        except EvidenceError:
            # Re-raise explicit adapter errors
            raise
        except Exception as e:
            logger.exception("Qdrant search failed")
            raise EvidenceError("QDRANT_COMMUNICATION_ERROR") from e

        if not candidates:
            return []

        # Candidates is a list of (UUID, score)
        candidate_ids = [cid for cid, score in candidates]
        score_map = {cid: score for cid, score in candidates}

        # 4. PostgreSQL Re-validation
        stmt = (
            select(RagChunk, RagPolicySource, RagSourceObject)
            .join(RagIngestionRun, RagChunk.run_id == RagIngestionRun.id)
            .join(RagPolicySource, RagIngestionRun.binding_id == RagPolicySource.id)
            .join(RagSourceObject, RagPolicySource.source_object_id == RagSourceObject.id)
            .join(RagIndexGeneration, RagIndexGeneration.run_id == RagIngestionRun.id)
            .where(
                RagChunk.institution_id == institution_id,
                RagIndexGeneration.id == generation.generation_id,
                RagChunk.id.in_(candidate_ids),
                RagPolicySource.policy_version_id == policy_version_id,
            )
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        chunk_map = {row.RagChunk.id: row for row in rows}
        evidence_list = []

        # 5. Assemble Verified Evidence
        # Maintain Qdrant's ordering by iterating over candidates
        for cid in candidate_ids:
            if cid in chunk_map:
                row = chunk_map[cid]
                chunk = row.RagChunk
                source = row.RagPolicySource
                obj = row.RagSourceObject
                
                citation = CitationMetadata(
                    document_id=obj.document_id,
                    source_hash=source.source_hash,
                    chunk_hash=chunk.chunk_hash,
                    ordinal=chunk.ordinal,
                    page=chunk.page,
                    section=chunk.section,
                    start_offset=chunk.start_offset,
                    end_offset=chunk.end_offset,
                )
                evidence = VerifiedEvidence(
                    text=chunk.content,
                    citation=citation,
                    score=score_map.get(cid),
                )
                evidence_list.append(evidence)
            else:
                logger.warning(
                    "Qdrant returned chunk %s not found in authorized PostgreSQL context", cid
                )

        return evidence_list
