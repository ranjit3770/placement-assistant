"""Staff-reviewed binding lifecycle only; approval is not publication.

The caller commits/rolls back a dedicated READ COMMITTED transaction per command.
Authenticated identity is injected by the application, never taken from source text.
Future retrieval must separately verify current policy context and generation.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import Principal
from app.infrastructure.models.rag import RagPolicySource
from app.rag.binding_repository import BindingRepository
from app.rag.contracts import (
    BindingState,
    DocumentStore,
    EvidenceError,
    validate_binding_transition,
)
from app.rag.source_service import SourceService


@dataclass(frozen=True)
class BindingEventView:
    sequence: int
    state: BindingState
    actor_id: UUID
    recorded_at: datetime
    request_id: UUID
    source_hash: str
    reason: str


@dataclass(frozen=True)
class BindingView:
    binding_id: UUID
    source_object_id: UUID
    policy_version_id: UUID
    revision: int
    previous_revision_id: UUID | None
    source_hash: str
    events: tuple[BindingEventView, ...]

    @property
    def state(self) -> BindingState:
        return self.events[-1].state


class BindingService:
    def __init__(self, session: AsyncSession, store: DocumentStore, principal: Principal) -> None:
        self.repository = BindingRepository(session, principal.institution_id)
        self.sources = SourceService(session, store, principal)
        self.principal = principal

    def _require_staff(self) -> None:
        if self.principal.role not in {"ADMIN", "COORDINATOR"}:
            raise EvidenceError("FORBIDDEN")

    @staticmethod
    def _validate_reason(reason: str) -> None:
        if not reason.strip() or len(reason) > 1000:
            raise EvidenceError("INVALID_BINDING_REASON")

    async def _view(self, binding: RagPolicySource) -> BindingView:
        events = await self.repository.events(binding.id)
        if not events or any(e.actor_id is None for e in events):
            raise EvidenceError("BINDING_HISTORY_INVALID")
        history = tuple(
            BindingEventView(
                e.sequence,
                BindingState(e.status),
                e.actor_id,
                e.recorded_at,
                e.request_id,
                e.source_hash,
                e.reason,
            )
            for e in events
            if e.actor_id is not None
        )
        return BindingView(
            binding.id,
            binding.source_object_id,
            binding.policy_version_id,
            binding.revision,
            binding.previous_revision_id,
            binding.source_hash,
            history,
        )

    async def inspect(self, binding_id: UUID) -> BindingView:
        self._require_staff()
        return await self._view(await self.repository.binding(binding_id))

    async def propose(
        self, document_id: UUID, policy_version_id: UUID, request_id: UUID, reason: str
    ) -> BindingView:
        self._require_staff()
        self._validate_reason(reason)
        await self.repository.require_policy(policy_version_id)
        await self.sources.read_for_review(document_id)
        source = await self.repository.source(document_id, lock=True)
        existing = await self.repository.proposal_request(request_id)
        if existing is not None:
            if (
                existing.source_object_id != source.id
                or existing.policy_version_id != policy_version_id
                or existing.actor_id != self.principal.sub
                or existing.proposal_reason != reason
            ):
                raise EvidenceError("IDEMPOTENCY_CONFLICT")
            return await self._view(existing)
        previous = await self.repository.latest_revision(source.id, policy_version_id)
        if previous is not None and (await self._view(previous)).state != BindingState.REVOKED:
            raise EvidenceError("BINDING_REVISION_STILL_OPEN")
        binding = await self.repository.insert_revision(
            source, policy_version_id, previous, self.principal.sub, request_id, reason
        )
        return await self._view(binding)

    async def approve(self, binding_id: UUID, request_id: UUID, reason: str) -> BindingView:
        return await self._transition(binding_id, BindingState.APPROVED, request_id, reason)

    async def revoke(self, binding_id: UUID, request_id: UUID, reason: str) -> BindingView:
        return await self._transition(binding_id, BindingState.REVOKED, request_id, reason)

    async def _transition(
        self, binding_id: UUID, target: BindingState, request_id: UUID, reason: str
    ) -> BindingView:
        self._require_staff()
        self._validate_reason(reason)
        binding = await self.repository.binding(binding_id, lock=True)
        view = await self._view(binding)
        existing = await self.repository.event_request(request_id)
        if existing is not None:
            if (
                existing.binding_id != binding_id
                or existing.status != target
                or existing.actor_id != self.principal.sub
                or existing.reason != reason
            ):
                raise EvidenceError("IDEMPOTENCY_CONFLICT")
            # Return CURRENT history, never resurrect an earlier approval on retry.
            return view
        validate_binding_transition(view.state, target)
        if target == BindingState.APPROVED:
            document_id = await self.repository.document_id(binding.source_object_id)
            await self.sources.read_for_review(document_id)
            source = await self.repository.source(document_id)
            if source.source_hash != binding.source_hash:
                raise EvidenceError("SOURCE_METADATA_MISMATCH")
        # Revocation must remain possible even if source storage is unavailable.
        await self.repository.append_event(
            binding, len(view.events) + 1, target, self.principal.sub, request_id, reason
        )
        return await self._view(binding)
