"""Tenant-scoped source metadata access; caller owns transaction boundaries."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.policy import Document
from app.infrastructure.models.rag import RagSourceObject
from app.rag.contracts import EvidenceError, SourceIdentity


class SourceRepository:
    def __init__(self, session: AsyncSession, institution_id: UUID) -> None:
        self.session = session
        self.institution_id = institution_id

    async def document_identity(self, document_id: UUID) -> SourceIdentity:
        result = await self.session.execute(
            select(Document.content_hash)
            .where(Document.institution_id == self.institution_id, Document.id == document_id)
            .with_for_update(read=True)
        )
        source_hash = result.scalar_one_or_none()
        if source_hash is None:
            raise EvidenceError("SOURCE_NOT_FOUND")
        return SourceIdentity(self.institution_id, document_id, source_hash)

    async def get(self, document_id: UUID) -> RagSourceObject | None:
        result = await self.session.execute(
            select(RagSourceObject)
            .where(
                RagSourceObject.institution_id == self.institution_id,
                RagSourceObject.document_id == document_id,
            )
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def record(
        self, identity: SourceIdentity, byte_length: int, actor_id: UUID
    ) -> RagSourceObject:
        if identity.institution_id != self.institution_id:
            raise EvidenceError("SOURCE_NOT_FOUND")
        await self.session.execute(
            insert(RagSourceObject)
            .values(
                institution_id=self.institution_id,
                document_id=identity.document_id,
                source_hash=identity.source_hash,
                object_key=identity.object_key,
                byte_length=byte_length,
                actor_id=actor_id,
                source_type="DOCUMENT",
                source_reference=f"document:{identity.document_id}",
                verification="VERIFIED",
            )
            .on_conflict_do_nothing(index_elements=["institution_id", "document_id"])
        )
        recorded = await self.get(identity.document_id)
        if recorded is None or (
            recorded.source_hash != identity.source_hash
            or recorded.object_key != identity.object_key
            or recorded.byte_length != byte_length
        ):
            raise EvidenceError("SOURCE_METADATA_MISMATCH")
        return recorded
