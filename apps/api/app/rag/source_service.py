"""Staff-only matching-byte import for existing M4 metadata.

Not an upload endpoint or retrieval service. MIME validation, new document
creation and approved policy binding are separate subsequent implementation work.
"""

import asyncio
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal
from app.infrastructure.models.rag import RagSourceObject
from app.rag.contracts import DocumentStore, EvidenceError, verify_source
from app.rag.source_repository import SourceRepository


class SourceService:
    def __init__(self, session: AsyncSession, store: DocumentStore, principal: Principal) -> None:
        self.repository = SourceRepository(session, principal.institution_id)
        self.store = store
        self.principal = principal

    def _require_staff(self) -> None:
        if self.principal.role not in {"ADMIN", "COORDINATOR"}:
            raise EvidenceError("FORBIDDEN")

    async def import_matching_bytes(self, document_id: UUID, data: bytes) -> RagSourceObject:
        self._require_staff()
        identity = await self.repository.document_identity(document_id)
        verify_source(identity, data)
        await asyncio.to_thread(self.store.preserve, identity, data)
        return await self.repository.record(identity, len(data), self.principal.sub)

    async def read_for_review(self, document_id: UUID) -> bytes:
        self._require_staff()
        identity = await self.repository.document_identity(document_id)
        recorded = await self.repository.get(document_id)
        if recorded is None:
            raise EvidenceError("SOURCE_UNAVAILABLE")
        if (
            recorded.source_hash != identity.source_hash
            or recorded.object_key != identity.object_key
        ):
            raise EvidenceError("SOURCE_METADATA_MISMATCH")
        data = await asyncio.to_thread(self.store.read_verified, identity)
        if len(data) != recorded.byte_length:
            raise EvidenceError("SOURCE_METADATA_MISMATCH")
        return data
