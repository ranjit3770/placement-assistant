from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime

from app.infrastructure.models.common import Revision, TenantRow, choices, revision_constraints, scoped_fk


class Document(TenantRow):
    __tablename__ = "policy_documents"
    storage_key: Mapped[str] = mapped_column(String(500))
    filename: Mapped[str]
    media_type: Mapped[str] = mapped_column(String(80))
    content_hash: Mapped[str] = mapped_column(String(64))
    source_version: Mapped[str] = mapped_column(String(80))
    constraints = (UniqueConstraint("institution_id", "storage_key"), CheckConstraint("content_hash ~ '^[0-9a-f]{64}$'", name="valid_hash"), choices("media_type", "application/pdf text/markdown text/plain"))


class SourceLocator(TenantRow):
    __tablename__ = "policy_source_locators"
    document_id: Mapped[UUID]
    page: Mapped[int | None]
    section: Mapped[str | None]
    start_offset: Mapped[int | None]
    end_offset: Mapped[int | None]
    constraints = (scoped_fk("document_id", "policy_documents"), CheckConstraint("page IS NULL OR page > 0", name="positive_page"), CheckConstraint("(start_offset IS NULL AND end_offset IS NULL) OR (start_offset IS NOT NULL AND end_offset IS NOT NULL AND start_offset >= 0 AND end_offset > start_offset)", name="offset_bounds"), CheckConstraint("page IS NOT NULL OR (section IS NOT NULL AND length(section) > 0) OR start_offset IS NOT NULL", name="locator_present"))


class Policy(TenantRow):
    __tablename__ = "policies"
    code: Mapped[str] = mapped_column(String(100))
    name: Mapped[str]
    constraints = (UniqueConstraint("institution_id", "code"),)


class PolicyVersion(Revision, TenantRow):
    __tablename__ = "policy_versions"
    policy_id: Mapped[UUID]
    academic_year_id: Mapped[UUID]
    scope: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", server_default="DRAFT")
    schema_version: Mapped[int]
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB)
    constraints = (*revision_constraints("policy_id", "policies"), scoped_fk("academic_year_id", "academic_years"), choices("status", "DRAFT PROCESSING REVIEW APPROVED ACTIVE ARCHIVED"), CheckConstraint("schema_version > 0 AND jsonb_typeof(definition) = 'object'", name="definition_shape"), UniqueConstraint("institution_id", "academic_year_id", "scope", "id"))


class PolicyEvent(Revision, TenantRow):
    __tablename__ = "policy_lifecycle_events"
    policy_version_id: Mapped[UUID]
    status: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str]
    constraints = (*revision_constraints("policy_version_id", "policy_versions"), choices("status", "DRAFT PROCESSING REVIEW APPROVED ACTIVE ARCHIVED"))


class PolicyRule(TenantRow):
    __tablename__ = "policy_rules"
    policy_version_id: Mapped[UUID]
    code: Mapped[str] = mapped_column(String(100))
    definition: Mapped[dict[str, Any]] = mapped_column(JSONB)
    constraints = (scoped_fk("policy_version_id", "policy_versions"), UniqueConstraint("institution_id", "policy_version_id", "code"), CheckConstraint("jsonb_typeof(definition) = 'object'", name="definition_object"))


class PolicyActivation(TenantRow):
    __tablename__ = "policy_activations"
    policy_version_id: Mapped[UUID]
    academic_year_id: Mapped[UUID]
    scope: Mapped[str] = mapped_column(String(100))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    constraints = (
        ForeignKeyConstraint(["institution_id", "academic_year_id", "scope", "policy_version_id"], ["policy_versions.institution_id", "policy_versions.academic_year_id", "policy_versions.scope", "policy_versions.id"]),
        CheckConstraint("ends_at IS NULL OR ends_at > starts_at", name="interval_bounds"),
        ExcludeConstraint(("institution_id", "="), ("academic_year_id", "="), ("scope", "="), (text("tstzrange(starts_at, ends_at, '[)')"), "&&"), name="ex_policy_activation_overlap", using="gist"),
    )


class Requirement(TenantRow):
    __tablename__ = "company_requirements"
    opportunity_id: Mapped[UUID]
    constraints = (scoped_fk("opportunity_id", "placement_opportunities"), UniqueConstraint("institution_id", "opportunity_id"))


class RequirementVersion(Revision, TenantRow):
    __tablename__ = "company_requirement_versions"
    requirement_id: Mapped[UUID]
    compensation_id: Mapped[UUID]
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    constraints = (*revision_constraints("requirement_id", "company_requirements"), scoped_fk("compensation_id", "compensation_terms"), UniqueConstraint("institution_id", "requirement_id", "id"))


class RequirementActivation(TenantRow):
    __tablename__ = "requirement_activations"
    requirement_id: Mapped[UUID]
    requirement_version_id: Mapped[UUID]
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    constraints = (
        ForeignKeyConstraint(["institution_id", "requirement_id", "requirement_version_id"], ["company_requirement_versions.institution_id", "company_requirement_versions.requirement_id", "company_requirement_versions.id"]),
        CheckConstraint("ends_at IS NULL OR ends_at > starts_at", name="interval_bounds"),
        ExcludeConstraint(("institution_id", "="), ("requirement_id", "="), (text("tstzrange(starts_at, ends_at, '[)')"), "&&"), name="ex_requirement_activation_overlap", using="gist"),
    )


class Criterion(TenantRow):
    __tablename__ = "requirement_criteria"
    requirement_version_id: Mapped[UUID]
    code: Mapped[str] = mapped_column(String(100))
    applicability: Mapped[str] = mapped_column(String(20))
    operator: Mapped[str | None] = mapped_column(String(12))
    operand: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    constraints = (scoped_fk("requirement_version_id", "company_requirement_versions"), UniqueConstraint("institution_id", "requirement_version_id", "code"), choices("applicability", "REQUIRED OPTIONAL NOT_APPLICABLE UNKNOWN"), choices("operator", "> >= < <= = != IN NOT_IN BETWEEN"), CheckConstraint("(applicability IN ('REQUIRED','OPTIONAL') AND operator IS NOT NULL AND operand IS NOT NULL AND jsonb_typeof(operand) = 'object') OR (applicability IN ('UNKNOWN','NOT_APPLICABLE') AND operator IS NULL AND operand IS NULL)", name="operand_presence"))


class RequirementMember(TenantRow):
    __tablename__ = "requirement_set_members"
    criterion_id: Mapped[UUID]
    value: Mapped[str] = mapped_column(String(200))
    department_id: Mapped[UUID | None]
    degree_id: Mapped[UUID | None]
    constraints = (scoped_fk("criterion_id", "requirement_criteria"), scoped_fk("department_id", "departments"), scoped_fk("degree_id", "degrees"), UniqueConstraint("institution_id", "criterion_id", "value"), CheckConstraint("department_id IS NULL OR degree_id IS NULL", name="single_member_type"))


class RuleSource(TenantRow):
    __tablename__ = "rule_source_links"
    rule_id: Mapped[UUID]
    locator_id: Mapped[UUID]
    constraints = (scoped_fk("rule_id", "policy_rules"), scoped_fk("locator_id", "policy_source_locators"), UniqueConstraint("institution_id", "rule_id", "locator_id"))


class RequirementSource(TenantRow):
    __tablename__ = "requirement_source_links"
    criterion_id: Mapped[UUID]
    locator_id: Mapped[UUID]
    constraints = (scoped_fk("criterion_id", "requirement_criteria"), scoped_fk("locator_id", "policy_source_locators"), UniqueConstraint("institution_id", "criterion_id", "locator_id"))
