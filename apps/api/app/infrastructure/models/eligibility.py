from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime

from app.infrastructure.models.common import TenantRow, choices, scoped_fk


class EligibilityDecision(TenantRow):
    __tablename__ = "eligibility_decisions"
    student_id: Mapped[UUID]
    opportunity_id: Mapped[UUID]
    policy_version_id: Mapped[UUID]
    requirement_version_id: Mapped[UUID]
    engine_version: Mapped[str] = mapped_column(String(50))
    result: Mapped[str] = mapped_column(String(20))
    evaluation_key: Mapped[str] = mapped_column(String(64))
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB)
    reasons: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    constraints = (
        scoped_fk("student_id", "students"),
        scoped_fk("opportunity_id", "placement_opportunities"),
        scoped_fk("policy_version_id", "policy_versions"),
        scoped_fk("requirement_version_id", "company_requirement_versions"),
        UniqueConstraint("institution_id", "evaluation_key"),
        choices("result", "ELIGIBLE NOT_ELIGIBLE UNKNOWN"),
        CheckConstraint("jsonb_typeof(snapshot) = 'object'", name="snapshot_object"),
        CheckConstraint("jsonb_typeof(reasons) = 'array'", name="reasons_array"),
    )
