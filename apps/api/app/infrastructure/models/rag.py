"""Additive M6 metadata. No relationships grant retrieval authorization."""

from uuid import UUID

from sqlalchemy import CheckConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.models.common import TenantRow, choices, scoped_fk


class RagSourceObject(TenantRow):
    __tablename__ = "rag_source_objects"

    document_id: Mapped[UUID]
    object_key: Mapped[str] = mapped_column(String(130))
    byte_length: Mapped[int]
    source_hash: Mapped[str] = mapped_column(String(64))

    constraints = (
        scoped_fk("document_id", "policy_documents"),
        UniqueConstraint("institution_id", "document_id"),
        UniqueConstraint("object_key"),
        CheckConstraint("byte_length > 0 AND byte_length <= 10485760", name="source_size"),
        CheckConstraint("source_hash ~ '^[0-9a-f]{64}$'", name="source_hash"),
        CheckConstraint(
            "object_key = replace(institution_id::text, '-', '') || '-' || "
            "replace(document_id::text, '-', '') || '-' || source_hash",
            name="source_key",
        ),
    )


class RagPolicySource(TenantRow):
    """Immutable document/policy association; status is derived from its events."""

    __tablename__ = "rag_policy_sources"

    source_object_id: Mapped[UUID]
    policy_version_id: Mapped[UUID]
    revision: Mapped[int]
    previous_revision_id: Mapped[UUID | None]
    source_hash: Mapped[str] = mapped_column(String(64))
    proposal_reason: Mapped[str] = mapped_column(String(1000))

    constraints = (
        scoped_fk("source_object_id", "rag_source_objects"),
        scoped_fk("policy_version_id", "policy_versions"),
        scoped_fk("previous_revision_id", "rag_policy_sources"),
        UniqueConstraint("institution_id", "source_object_id", "policy_version_id", "revision"),
        UniqueConstraint("institution_id", "request_id"),
        CheckConstraint("revision > 0", name="positive_revision"),
        CheckConstraint("actor_id IS NOT NULL", name="binding_actor_required"),
        CheckConstraint("source_hash ~ '^[0-9a-f]{64}$'", name="binding_hash"),
        CheckConstraint("length(trim(proposal_reason)) > 0", name="proposal_reason_required"),
    )


class RagBindingEvent(TenantRow):
    __tablename__ = "rag_binding_events"

    binding_id: Mapped[UUID]
    sequence: Mapped[int]
    status: Mapped[str] = mapped_column(String(20))
    source_hash: Mapped[str] = mapped_column(String(64))
    reason: Mapped[str] = mapped_column(String(1000))

    constraints = (
        scoped_fk("binding_id", "rag_policy_sources"),
        UniqueConstraint("institution_id", "binding_id", "sequence"),
        UniqueConstraint("institution_id", "request_id"),
        choices("status", "PROPOSED APPROVED REVOKED"),
        CheckConstraint(
            "(sequence = 1 AND status = 'PROPOSED') OR "
            "(sequence = 2 AND status = 'APPROVED') OR "
            "(sequence = 3 AND status = 'REVOKED')",
            name="event_sequence_state",
        ),
        CheckConstraint("actor_id IS NOT NULL", name="event_actor_required"),
        CheckConstraint("source_hash ~ '^[0-9a-f]{64}$'", name="event_hash"),
        CheckConstraint("length(trim(reason)) > 0", name="event_reason_required"),
    )
