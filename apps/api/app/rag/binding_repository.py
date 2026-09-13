"""Tenant-scoped binding persistence; no eligibility or retrieval decisions."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.models.policy import PolicyVersion
from app.infrastructure.models.rag import RagBindingEvent, RagPolicySource, RagSourceObject
from app.rag.contracts import EvidenceError


class BindingRepository:
    def __init__(self, session: AsyncSession, institution_id: UUID) -> None:
        self.session = session
        self.institution_id = institution_id

    async def require_policy(self, policy_version_id: UUID) -> None:
        found = await self.session.scalar(
            select(PolicyVersion.id).where(
                PolicyVersion.institution_id == self.institution_id,
                PolicyVersion.id == policy_version_id,
            )
        )
        if found is None:
            raise EvidenceError("POLICY_NOT_FOUND")

    async def source(self, document_id: UUID, *, lock: bool = False) -> RagSourceObject:
        query = select(RagSourceObject).where(
            RagSourceObject.institution_id == self.institution_id,
            RagSourceObject.document_id == document_id,
        )
        if lock:
            query = query.with_for_update()
        found = await self.session.scalar(query.execution_options(populate_existing=True))
        if found is None:
            raise EvidenceError("SOURCE_UNAVAILABLE")
        return found

    async def binding(self, binding_id: UUID, *, lock: bool = False) -> RagPolicySource:
        query = select(RagPolicySource).where(
            RagPolicySource.institution_id == self.institution_id,
            RagPolicySource.id == binding_id,
        )
        if lock:
            query = query.with_for_update()
        found = await self.session.scalar(query.execution_options(populate_existing=True))
        if found is None:
            raise EvidenceError("BINDING_NOT_FOUND")
        return found

    async def document_id(self, source_object_id: UUID) -> UUID:
        found = await self.session.scalar(
            select(RagSourceObject.document_id).where(
                RagSourceObject.institution_id == self.institution_id,
                RagSourceObject.id == source_object_id,
            )
        )
        if found is None:
            raise EvidenceError("SOURCE_UNAVAILABLE")
        return found

    async def proposal_request(self, request_id: UUID) -> RagPolicySource | None:
        return await self.session.scalar(
            select(RagPolicySource).where(
                RagPolicySource.institution_id == self.institution_id,
                RagPolicySource.request_id == request_id,
            )
        )

    async def event_request(self, request_id: UUID) -> RagBindingEvent | None:
        return await self.session.scalar(
            select(RagBindingEvent).where(
                RagBindingEvent.institution_id == self.institution_id,
                RagBindingEvent.request_id == request_id,
            )
        )

    async def latest_revision(
        self, source_object_id: UUID, policy_version_id: UUID
    ) -> RagPolicySource | None:
        return await self.session.scalar(
            select(RagPolicySource)
            .where(
                RagPolicySource.institution_id == self.institution_id,
                RagPolicySource.source_object_id == source_object_id,
                RagPolicySource.policy_version_id == policy_version_id,
            )
            .order_by(RagPolicySource.revision.desc())
            .limit(1)
        )

    async def events(self, binding_id: UUID) -> Sequence[RagBindingEvent]:
        result = await self.session.scalars(
            select(RagBindingEvent)
            .where(
                RagBindingEvent.institution_id == self.institution_id,
                RagBindingEvent.binding_id == binding_id,
            )
            .order_by(RagBindingEvent.sequence)
        )
        return result.all()

    async def insert_revision(
        self,
        source: RagSourceObject,
        policy_version_id: UUID,
        previous: RagPolicySource | None,
        actor_id: UUID,
        request_id: UUID,
        reason: str,
    ) -> RagPolicySource:
        if source.institution_id != self.institution_id or (
            previous is not None and previous.institution_id != self.institution_id
        ):
            raise EvidenceError("BINDING_NOT_FOUND")
        binding = RagPolicySource(
            institution_id=self.institution_id,
            source_object_id=source.id,
            policy_version_id=policy_version_id,
            revision=1 if previous is None else previous.revision + 1,
            previous_revision_id=None if previous is None else previous.id,
            source_hash=source.source_hash,
            proposal_reason=reason,
            actor_id=actor_id,
            request_id=request_id,
            source_type="DOCUMENT",
            source_reference=f"source:{source.id}",
            verification="VERIFIED",
        )
        self.session.add(binding)
        # PostgreSQL creates the initial PROPOSED event in this same statement.
        await self.session.flush()
        return binding

    async def append_event(
        self,
        binding: RagPolicySource,
        sequence: int,
        status: str,
        actor_id: UUID,
        request_id: UUID,
        reason: str,
    ) -> None:
        if binding.institution_id != self.institution_id:
            raise EvidenceError("BINDING_NOT_FOUND")
        self.session.add(
            RagBindingEvent(
                institution_id=self.institution_id,
                binding_id=binding.id,
                sequence=sequence,
                status=status,
                source_hash=binding.source_hash,
                actor_id=actor_id,
                request_id=request_id,
                reason=reason,
                source_type="DOCUMENT",
                source_reference=f"binding:{binding.id}",
                verification="VERIFIED",
            )
        )
        await self.session.flush()
