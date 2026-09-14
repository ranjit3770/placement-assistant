"""Additive M6 metadata. No relationships grant retrieval authorization."""

import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, String, UniqueConstraint, DateTime
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


class RagIngestionRun(TenantRow):
    __tablename__ = "rag_ingestion_runs"

    binding_id: Mapped[UUID]
    schema_version: Mapped[int]
    parser_version: Mapped[str] = mapped_column(String(50))
    chunker_version: Mapped[str] = mapped_column(String(50))
    embedding_configuration: Mapped[str] = mapped_column(String(200))
    normalized_artifact_hash: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20))

    constraints = (
        scoped_fk("binding_id", "rag_policy_sources"),
        UniqueConstraint(
            "institution_id",
            "binding_id",
            "schema_version",
            "parser_version",
            "chunker_version",
            "embedding_configuration",
            name="uq_rag_ingestion_run_idempotency",
        ),
        choices("status", "RUNNING FAILED COMPLETED"),
        CheckConstraint("schema_version > 0", name="positive_schema_version"),
        CheckConstraint(
            "normalized_artifact_hash IS NULL OR normalized_artifact_hash ~ '^[0-9a-f]{64}$'",
            name="artifact_hash_format",
        ),
        CheckConstraint("length(trim(parser_version)) > 0", name="parser_version_required"),
        CheckConstraint("length(trim(chunker_version)) > 0", name="chunker_version_required"),
        CheckConstraint(
            "length(trim(embedding_configuration)) > 0", name="embedding_configuration_required"
        ),
    )


class RagJob(TenantRow):
    __tablename__ = "rag_jobs"

    run_id: Mapped[UUID]
    status: Mapped[str] = mapped_column(String(20))
    attempt: Mapped[int]
    leased_until: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    stage: Mapped[str] = mapped_column(String(50))
    error_code: Mapped[str | None] = mapped_column(String(100))

    constraints = (
        scoped_fk("run_id", "rag_ingestion_runs"),
        UniqueConstraint("institution_id", "run_id"),
        choices("status", "QUEUED RUNNING READY REVIEW_REQUIRED FAILED CANCELLED"),
        CheckConstraint("attempt >= 0 AND attempt <= 3", name="job_attempt_bounds"),
        CheckConstraint("length(trim(stage)) > 0", name="stage_required"),
    )


class RagChunk(TenantRow):
    __tablename__ = "rag_chunks"

    run_id: Mapped[UUID]
    ordinal: Mapped[int]
    content: Mapped[str] = mapped_column(String)
    page: Mapped[int | None]
    section: Mapped[str | None] = mapped_column(String(200))
    start_offset: Mapped[int | None]
    end_offset: Mapped[int | None]
    source_hash: Mapped[str] = mapped_column(String(64))
    artifact_hash: Mapped[str] = mapped_column(String(64))
    chunk_hash: Mapped[str] = mapped_column(String(64))

    constraints = (
        scoped_fk("run_id", "rag_ingestion_runs"),
        UniqueConstraint("institution_id", "run_id", "ordinal"),
        CheckConstraint("ordinal >= 0", name="chunk_ordinal_bounds"),
        CheckConstraint("source_hash ~ '^[0-9a-f]{64}$'", name="chunk_source_hash"),
        CheckConstraint("artifact_hash ~ '^[0-9a-f]{64}$'", name="chunk_artifact_hash"),
        CheckConstraint("chunk_hash ~ '^[0-9a-f]{64}$'", name="chunk_hash_format"),
        CheckConstraint("page IS NULL OR page > 0", name="chunk_page_bounds"),
        CheckConstraint(
            "(start_offset IS NULL AND end_offset IS NULL) OR "
            "(start_offset IS NOT NULL AND end_offset IS NOT NULL AND start_offset >= 0 AND end_offset > start_offset)",
            name="chunk_offset_bounds",
        ),
        CheckConstraint(
            "page IS NOT NULL OR (section IS NOT NULL AND length(section) > 0) OR start_offset IS NOT NULL",
            name="chunk_locator_present",
        ),
    )


class RagIndexGeneration(TenantRow):
    __tablename__ = "rag_index_generations"

    run_id: Mapped[UUID]
    space_id: Mapped[str] = mapped_column(String(64))
    collection_name: Mapped[str] = mapped_column(String(200))
    expected_chunk_count: Mapped[int]
    status: Mapped[str] = mapped_column(String(20))

    constraints = (
        scoped_fk("run_id", "rag_ingestion_runs"),
        UniqueConstraint("institution_id", "run_id", "space_id"),
        choices("status", "PENDING VERIFIED PUBLISHED FAILED"),
        CheckConstraint("expected_chunk_count >= 0", name="generation_chunk_count_bounds"),
        CheckConstraint("space_id ~ '^[0-9a-f]{64}$'", name="generation_space_id_format"),
        CheckConstraint("length(trim(collection_name)) > 0", name="generation_collection_name_required"),
    )


class RagPublishedGeneration(TenantRow):
    __tablename__ = "rag_published_generations"

    binding_id: Mapped[UUID]
    generation_id: Mapped[UUID]
    published_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))

    constraints = (
        scoped_fk("binding_id", "rag_policy_sources"),
        scoped_fk("generation_id", "rag_index_generations"),
        UniqueConstraint("institution_id", "binding_id"),
        UniqueConstraint("institution_id", "generation_id"),
    )
