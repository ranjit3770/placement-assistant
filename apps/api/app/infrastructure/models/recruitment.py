from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import DateTime

from app.infrastructure.models.common import Revision, TenantRow, choices, revision_constraints, scoped_fk


class Company(TenantRow):
    __tablename__ = "companies"
    code: Mapped[str] = mapped_column(String(100))
    constraints = (UniqueConstraint("institution_id", "code"),)


class CompanyRevision(Revision, TenantRow):
    __tablename__ = "company_revisions"
    company_id: Mapped[UUID]
    name: Mapped[str]
    constraints = revision_constraints("company_id", "companies")


class CompanyRole(TenantRow):
    __tablename__ = "company_roles"
    company_id: Mapped[UUID]
    code: Mapped[str] = mapped_column(String(100))
    title: Mapped[str]
    constraints = (scoped_fk("company_id", "companies"), UniqueConstraint("institution_id", "company_id", "code"), UniqueConstraint("institution_id", "company_id", "id"))


class Drive(TenantRow):
    __tablename__ = "placement_drives"
    company_id: Mapped[UUID]
    academic_year_id: Mapped[UUID]
    announced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", server_default="DRAFT")
    constraints = (scoped_fk("company_id", "companies"), scoped_fk("academic_year_id", "academic_years"), UniqueConstraint("institution_id", "company_id", "id"), UniqueConstraint("institution_id", "academic_year_id", "id"), choices("status", "DRAFT ANNOUNCED CLOSED CANCELLED"), CheckConstraint("status = 'DRAFT' OR announced_at IS NOT NULL", name="announcement_required"))


class Opportunity(TenantRow):
    __tablename__ = "placement_opportunities"
    company_id: Mapped[UUID]
    role_id: Mapped[UUID]
    drive_id: Mapped[UUID]
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", server_default="DRAFT")
    constraints = (
        ForeignKeyConstraint(["institution_id", "company_id", "role_id"], ["company_roles.institution_id", "company_roles.company_id", "company_roles.id"]),
        ForeignKeyConstraint(["institution_id", "company_id", "drive_id"], ["placement_drives.institution_id", "placement_drives.company_id", "placement_drives.id"]),
        UniqueConstraint("institution_id", "company_id", "role_id", "id"),
        UniqueConstraint("institution_id", "drive_id", "role_id"), choices("status", "DRAFT OPEN CLOSED CANCELLED"),
    )


class Compensation(TenantRow):
    __tablename__ = "compensation_terms"
    original_text: Mapped[str]
    currency: Mapped[str] = mapped_column(String(3))
    period: Mapped[str] = mapped_column(String(20))
    basis: Mapped[str] = mapped_column(String(30))
    shape: Mapped[str] = mapped_column(String(20))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    minimum: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    maximum: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    comparison_state: Mapped[str] = mapped_column(String(20))
    annual_inr: Mapped[Decimal | None] = mapped_column(Numeric(18, 4))
    review_reason: Mapped[str | None]
    constraints = (
        choices("period", "ANNUAL MONTHLY HOURLY UNKNOWN"),
        choices("basis", "TOTAL_CTC FIXED_PAY EQUITY_HEAVY OTHER UNKNOWN"),
        choices("shape", "EXACT RANGE UNKNOWN"), choices("comparison_state", "COMPARABLE UNRESOLVED"),
        CheckConstraint("currency ~ '^[A-Z]{3}$'", name="currency_code"),
        CheckConstraint("(shape = 'EXACT' AND amount IS NOT NULL AND minimum IS NULL AND maximum IS NULL) OR (shape = 'RANGE' AND amount IS NULL AND minimum IS NOT NULL AND maximum IS NOT NULL AND minimum <= maximum) OR (shape = 'UNKNOWN' AND amount IS NULL AND minimum IS NULL AND maximum IS NULL)", name="shape_amounts"),
        CheckConstraint("(amount IS NULL OR (amount >= 0 AND amount < 'Infinity'::numeric)) AND (minimum IS NULL OR (minimum >= 0 AND minimum < 'Infinity'::numeric)) AND (maximum IS NULL OR (maximum >= 0 AND maximum < 'Infinity'::numeric))", name="finite_nonnegative"),
        CheckConstraint("(comparison_state = 'COMPARABLE' AND currency = 'INR' AND period = 'ANNUAL' AND basis = 'TOTAL_CTC' AND shape = 'EXACT' AND verification = 'VERIFIED' AND annual_inr IS NOT NULL AND annual_inr = amount AND review_reason IS NULL) OR (comparison_state = 'UNRESOLVED' AND annual_inr IS NULL AND review_reason IS NOT NULL AND length(review_reason) > 0)", name="comparable_terms"),
    )


class Offer(TenantRow):
    __tablename__ = "student_offers"
    student_id: Mapped[UUID]
    company_id: Mapped[UUID]
    role_id: Mapped[UUID]
    opportunity_id: Mapped[UUID | None]
    academic_year_id: Mapped[UUID]
    context: Mapped[str] = mapped_column(String(100))
    constraints = (
        scoped_fk("student_id", "students"), scoped_fk("academic_year_id", "academic_years"),
        ForeignKeyConstraint(["institution_id", "company_id", "role_id"], ["company_roles.institution_id", "company_roles.company_id", "company_roles.id"]),
        ForeignKeyConstraint(["institution_id", "company_id", "role_id", "opportunity_id"], ["placement_opportunities.institution_id", "placement_opportunities.company_id", "placement_opportunities.role_id", "placement_opportunities.id"]),
        CheckConstraint("length(context) > 0", name="context_present"),
    )


class OfferEvent(Revision, TenantRow):
    __tablename__ = "student_offer_events"
    offer_id: Mapped[UUID]
    kind: Mapped[str] = mapped_column(String(20))
    compensation_id: Mapped[UUID | None]
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    import_key: Mapped[str | None] = mapped_column(String(200))
    constraints = (*revision_constraints("offer_id", "student_offers"), scoped_fk("compensation_id", "compensation_terms"), UniqueConstraint("institution_id", "offer_id", "import_key"), choices("kind", "RECEIVED ACCEPTED REJECTED REVOKED WITHDRAWN EXPIRED TERMS_REVISED CORRECTED"), CheckConstraint("kind NOT IN ('RECEIVED','ACCEPTED','TERMS_REVISED') OR compensation_id IS NOT NULL", name="terms_required"), CheckConstraint("expires_at IS NULL OR expires_at > effective_at", name="expiry_order"))


class DreamDeclaration(TenantRow):
    __tablename__ = "student_dream_companies"
    student_id: Mapped[UUID]
    company_id: Mapped[UUID]
    academic_year_id: Mapped[UUID]
    constraints = (scoped_fk("student_id", "students"), scoped_fk("company_id", "companies"), scoped_fk("academic_year_id", "academic_years"), UniqueConstraint("institution_id", "student_id", "academic_year_id", "id"))


class DreamEvent(Revision, TenantRow):
    __tablename__ = "dream_declaration_events"
    declaration_id: Mapped[UUID]
    kind: Mapped[str] = mapped_column(String(20))
    policy_version_id: Mapped[UUID | None]
    constraints = (*revision_constraints("declaration_id", "student_dream_companies"), scoped_fk("policy_version_id", "policy_versions"), choices("kind", "DECLARED APPROVED REJECTED REVOKED SUPERSEDED"), UniqueConstraint("institution_id", "declaration_id", "id"))


class DreamLock(TenantRow):
    __tablename__ = "dream_drive_locks"
    student_id: Mapped[UUID]
    academic_year_id: Mapped[UUID]
    declaration_id: Mapped[UUID]
    approval_event_id: Mapped[UUID]
    drive_id: Mapped[UUID]
    policy_version_id: Mapped[UUID]
    announced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    constraints = (
        ForeignKeyConstraint(["institution_id", "student_id", "academic_year_id", "declaration_id"], ["student_dream_companies.institution_id", "student_dream_companies.student_id", "student_dream_companies.academic_year_id", "student_dream_companies.id"]),
        ForeignKeyConstraint(["institution_id", "declaration_id", "approval_event_id"], ["dream_declaration_events.institution_id", "dream_declaration_events.declaration_id", "dream_declaration_events.id"]),
        ForeignKeyConstraint(["institution_id", "academic_year_id", "drive_id"], ["placement_drives.institution_id", "placement_drives.academic_year_id", "placement_drives.id"]),
        scoped_fk("policy_version_id", "policy_versions"), UniqueConstraint("institution_id", "student_id", "drive_id", "declaration_id"),
    )
