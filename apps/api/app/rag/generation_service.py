import uuid
from datetime import UTC, datetime
from collections.abc import Sequence

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.infrastructure.models.rag import (
    RagChunk,
    RagIndexGeneration,
    RagIngestionRun,
    RagPolicySource,
    RagPublishedGeneration,
)
from app.rag.contracts import (
    EvidenceError,
    ManifestPoint,
    validate_manifest,
    validate_vectors,
    sha256,
)
from app.rag.embedding_provider import HTTPEmbeddingProvider
from app.rag.qdrant_adapter import QdrantAdapter


class GenerationService:
    def __init__(
        self,
        session: AsyncSession,
        institution_id: uuid.UUID,
        embedding_provider: HTTPEmbeddingProvider,
        qdrant: QdrantAdapter,
    ) -> None:
        self.session = session
        self.institution_id = institution_id
        self.embedding_provider = embedding_provider
        self.qdrant = qdrant

    async def generate_index(self, run_id: uuid.UUID) -> uuid.UUID:
        """
        Orchestrates M6 Increment 4:
        Load COMPLETED run -> Validate chunks -> Create PENDING generation -> 
        Generate embeddings -> Upsert Qdrant -> Verify manifest -> VERIFIED -> PUBLISH (Atomic)
        """
        # 1. Load COMPLETED run
        run_stmt = select(RagIngestionRun).where(
            RagIngestionRun.id == run_id,
            RagIngestionRun.institution_id == self.institution_id,
        )
        run = await self.session.scalar(run_stmt)
        if not run:
            raise EvidenceError("RUN_NOT_FOUND")
        if run.status != "COMPLETED":
            raise EvidenceError("RUN_NOT_COMPLETED")

        # Load binding to get metadata
        binding_stmt = select(RagPolicySource).where(
            RagPolicySource.id == run.binding_id,
            RagPolicySource.institution_id == self.institution_id,
        )
        binding = await self.session.scalar(binding_stmt)
        if not binding:
            raise EvidenceError("BINDING_NOT_FOUND")

        # Load chunks
        chunks_stmt = select(RagChunk).where(RagChunk.run_id == run_id).order_by(RagChunk.ordinal)
        chunks = (await self.session.scalars(chunks_stmt)).all()
        if not chunks:
            raise EvidenceError("NO_CHUNKS_FOUND")

        # 2. Validate chunks (basic count for generation)
        expected_chunk_count = len(chunks)

        # 3. Create PENDING generation
        space = self.embedding_provider.space
        space_id = space.space_id
        
        # Collection name: rag_<institution_uuid>_<space_hash>
        collection_name = f"rag_{self.institution_id.hex}_{space_id}"

        gen = RagIndexGeneration(
            institution_id=self.institution_id,
            run_id=run_id,
            space_id=space_id,
            collection_name=collection_name,
            expected_chunk_count=expected_chunk_count,
            status="PENDING",
            source_type="SYSTEM",
            source_reference="M6",
        )
        self.session.add(gen)
        try:
            await self.session.flush()
        except IntegrityError as e:
            # If a generation already exists for this run and space, fetch it.
            # Retry idempotency: if it failed, we can retry. If it's published, no need.
            await self.session.rollback()
            existing_stmt = select(RagIndexGeneration).where(
                RagIndexGeneration.run_id == run_id,
                RagIndexGeneration.space_id == space_id,
            )
            existing = await self.session.scalar(existing_stmt)
            if existing and existing.status in ("VERIFIED", "PUBLISHED"):
                return existing.id
            elif existing:
                # Reuse the existing PENDING/FAILED generation for retry
                gen = existing
                gen.status = "PENDING"
                self.session.add(gen)
                await self.session.flush()
            else:
                raise EvidenceError("GENERATION_CONFLICT") from e

        generation_id = gen.id

        # If we had to rollback, the previously loaded objects (run, binding, chunks)
        # became expired. We need to refresh/re-load them to avoid MissingGreenlet.
        run = await self.session.scalar(select(RagIngestionRun).where(RagIngestionRun.id == run_id))
        binding = await self.session.scalar(select(RagPolicySource).where(RagPolicySource.id == run.binding_id))
        chunks_stmt = select(RagChunk).where(RagChunk.run_id == run_id).order_by(RagChunk.ordinal)
        chunks = (await self.session.scalars(chunks_stmt)).all()

        # 4. Generate embeddings
        texts = [c.content for c in chunks]
        try:
            vectors = await self.embedding_provider.embed(texts)
            validate_vectors(space, vectors, expected_chunk_count)
        except Exception as e:
            gen.status = "FAILED"
            await self.session.commit()
            raise EvidenceError("EMBEDDING_GENERATION_FAILED") from e

        # 5. Upsert Qdrant
        points = []
        expected_manifest = []
        
        # We need a stable UUID namespace for point IDs.
        # As requested: vector_id = SHA256(canonical_embedding_space + ":" + chunk_hash) converted to UUID.
        # space_id is already the sha256 of canonical_embedding_space.
        for chunk, vector in zip(chunks, vectors, strict=True):
            # Deterministic ID
            vector_id_hash = sha256(f"{space_id}:{chunk.chunk_hash}".encode("utf-8"))
            point_id = uuid.UUID(vector_id_hash[:32])

            payload = {
                "chunk_hash": chunk.chunk_hash,
                "artifact_hash": chunk.artifact_hash,
                "source_hash": chunk.source_hash,
                "institution_id": str(self.institution_id),
                "binding_id": str(binding.id),
                "policy_version_id": str(binding.policy_version_id),
                "generation_id": str(generation_id),
                "embedding_space_id": space_id,
                "text": chunk.content,  # In real systems, this could be excluded from vector DB if Postgres handles retrieval
            }
            points.append({
                "id": str(point_id),
                "vector": vector,
                "payload": payload
            })
            expected_manifest.append(ManifestPoint(point_id=point_id, chunk_hash=chunk.chunk_hash))

        try:
            await self.qdrant.ensure_collection(collection_name, space.dimensions, space.distance_metric)
            await self.qdrant.upsert_points(collection_name, points)
        except Exception as e:
            gen.status = "FAILED"
            await self.session.commit()
            raise EvidenceError("QDRANT_UPSERT_FAILED") from e

        # 6. Verify manifest strictly
        try:
            actual_manifest = await self.qdrant.fetch_manifest(collection_name, generation_id, expected_chunk_count)
            validate_manifest(expected_manifest, actual_manifest)
        except Exception as e:
            gen.status = "FAILED"
            await self.session.commit()
            raise EvidenceError("MANIFEST_VERIFICATION_FAILED") from e

        # 7. Transition to VERIFIED and PUBLISH atomically
        gen.status = "VERIFIED"
        await self.session.flush()

        # Update or create RagPublishedGeneration
        pub_stmt = select(RagPublishedGeneration).where(
            RagPublishedGeneration.institution_id == self.institution_id,
            RagPublishedGeneration.binding_id == binding.id,
        ).with_for_update()
        
        pub = await self.session.scalar(pub_stmt)
        if pub:
            pub.generation_id = generation_id
            pub.published_at = datetime.now(UTC)
        else:
            pub = RagPublishedGeneration(
                institution_id=self.institution_id,
                binding_id=binding.id,
                generation_id=generation_id,
                published_at=datetime.now(UTC),
                source_type="SYSTEM",
                source_reference="M6",
            )
            self.session.add(pub)

        gen.status = "PUBLISHED"
        await self.session.commit()
        return generation_id
