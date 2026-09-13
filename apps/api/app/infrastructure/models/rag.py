"""Additive M6 metadata. No relationships grant retrieval authorization."""

from uuid import UUID

from sqlalchemy import CheckConstraint, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.models.common import TenantRow, scoped_fk


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
