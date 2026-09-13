from datetime import datetime
from typing import ClassVar
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, declared_attr, mapped_column
from sqlalchemy.schema import SchemaItem
from sqlalchemy.types import DateTime

from app.infrastructure.database import Base


def scoped_fk(column: str, parent: str) -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        ["institution_id", column],
        [f"{parent}.institution_id", f"{parent}.id"],
        ondelete="RESTRICT",
    )


def choices(column: str, values: str) -> CheckConstraint:
    quoted = ",".join(f"'{v}'" for v in values.split())
    return CheckConstraint(f"{column} IN ({quoted})", name=f"{column}_values")


class TenantRow(Base):
    __abstract__ = True
    constraints: ClassVar[tuple[SchemaItem, ...]] = ()
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    institution_id: Mapped[UUID] = mapped_column(
        ForeignKey("institutions.id", ondelete="RESTRICT"), index=True
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    actor_id: Mapped[UUID | None]
    request_id: Mapped[UUID] = mapped_column(default=uuid4, server_default=func.gen_random_uuid())
    source_type: Mapped[str] = mapped_column(String(24))
    source_reference: Mapped[str] = mapped_column(String(500))
    verification: Mapped[str] = mapped_column(
        String(20), default="UNVERIFIED", server_default="UNVERIFIED"
    )
    correction_reason: Mapped[str | None]

    @declared_attr.directive
    def __table_args__(cls) -> tuple[SchemaItem, ...]:
        return (
            UniqueConstraint("institution_id", "id"),
            scoped_fk("actor_id", "users"),
            choices("source_type", "INSTITUTION IMPORT DOCUMENT STUDENT SYSTEM"),
            choices("verification", "VERIFIED SELF_DECLARED UNVERIFIED"),
            CheckConstraint("length(source_reference) > 0", name="source_present"),
            *cls.constraints,
        )


class Revision:
    version: Mapped[int]
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


def revision_constraints(parent: str, table: str) -> tuple[SchemaItem, ...]:
    return (
        scoped_fk(parent, table),
        UniqueConstraint("institution_id", parent, "version"),
        CheckConstraint("version > 0", name="positive_version"),
    )
