from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime

from app.infrastructure.database import Base
from app.infrastructure.models.common import (
    TenantRow,
    Revision,
    choices,
    revision_constraints,
    scoped_fk,
)


class Institution(Base):
    __tablename__ = "institutions"
    id: Mapped[UUID] = mapped_column(
        primary_key=True, default=uuid4, server_default=func.gen_random_uuid()
    )
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str]


class Role(Base):
    __tablename__ = "roles"
    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    __table_args__ = (choices("code", "STUDENT COORDINATOR ADMIN"),)


class User(TenantRow):
    __tablename__ = "users"
    login: Mapped[str] = mapped_column(String(254))
    status: Mapped[str] = mapped_column(String(20), default="DISABLED", server_default="DISABLED")
    constraints = (
        UniqueConstraint("institution_id", "login"),
        choices("status", "ACTIVE DISABLED"),
        CheckConstraint("login = lower(login) AND length(login) > 0", name="normalized_login"),
    )


class UserRole(TenantRow):
    __tablename__ = "user_roles"
    user_id: Mapped[UUID]
    role_code: Mapped[str] = mapped_column(ForeignKey("roles.code"))
    constraints = (
        scoped_fk("user_id", "users"),
        UniqueConstraint("institution_id", "user_id", "role_code"),
    )


class AcademicYear(TenantRow):
    __tablename__ = "academic_years"
    code: Mapped[str] = mapped_column(String(40))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    constraints = (
        UniqueConstraint("institution_id", "code"),
        CheckConstraint("starts_at < ends_at", name="valid_interval"),
    )


class Department(TenantRow):
    __tablename__ = "departments"
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str]
    constraints = (UniqueConstraint("institution_id", "code"),)


class Degree(TenantRow):
    __tablename__ = "degrees"
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str]
    constraints = (UniqueConstraint("institution_id", "code"),)


class Student(TenantRow):
    __tablename__ = "students"
    roll_number: Mapped[str] = mapped_column(String(80))
    user_id: Mapped[UUID | None]
    constraints = (
        UniqueConstraint("institution_id", "roll_number"),
        UniqueConstraint("institution_id", "user_id"),
        scoped_fk("user_id", "users"),
    )
    revisions: Mapped[list["StudentRevision"]] = relationship(
        primaryjoin="and_(Student.institution_id == StudentRevision.institution_id, Student.id == StudentRevision.student_id)",
        viewonly=True,
        lazy="raise",
        order_by="StudentRevision.version",
    )


class StudentRevision(Revision, TenantRow):
    __tablename__ = "student_revisions"
    student_id: Mapped[UUID]
    full_name: Mapped[str]
    department_id: Mapped[UUID | None]
    degree_id: Mapped[UUID | None]
    graduation_year: Mapped[int | None]
    constraints = (
        *revision_constraints("student_id", "students"),
        scoped_fk("department_id", "departments"),
        scoped_fk("degree_id", "degrees"),
        CheckConstraint("graduation_year BETWEEN 1900 AND 2500", name="year_range"),
    )


class GradingScale(TenantRow):
    __tablename__ = "grading_scales"
    code: Mapped[str] = mapped_column(String(40))
    minimum: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    maximum: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    constraints = (
        UniqueConstraint("institution_id", "code"),
        CheckConstraint(
            "minimum >= 0 AND maximum > minimum AND maximum < 'Infinity'::numeric",
            name="scale_bounds",
        ),
    )


def mark_constraints(name: str, maximum: str = "100") -> tuple[CheckConstraint, ...]:
    return (
        choices(f"{name}_state", "KNOWN UNKNOWN NOT_APPLICABLE"),
        CheckConstraint(
            f"({name}_state = 'KNOWN' AND {name} IS NOT NULL AND {name} >= 0 AND {name} <= {maximum}) OR ({name}_state != 'KNOWN' AND {name} IS NULL)",
            name=f"{name}_presence",
        ),
    )


class AcademicRecord(Revision, TenantRow):
    __tablename__ = "student_academic_records"
    student_id: Mapped[UUID]
    sslc: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    sslc_state: Mapped[str] = mapped_column(String(20))
    hsc: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    hsc_state: Mapped[str] = mapped_column(String(20))
    diploma: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    diploma_state: Mapped[str] = mapped_column(String(20))
    cgpa: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    cgpa_state: Mapped[str] = mapped_column(String(20))
    scale_id: Mapped[UUID | None]
    constraints = (
        *revision_constraints("student_id", "students"),
        scoped_fk("scale_id", "grading_scales"),
        *mark_constraints("sslc"),
        *mark_constraints("hsc"),
        *mark_constraints("diploma"),
        *mark_constraints("cgpa", "999999"),
        CheckConstraint("cgpa_state != 'KNOWN' OR scale_id IS NOT NULL", name="cgpa_scale"),
    )


class SemesterRecord(TenantRow):
    __tablename__ = "student_semester_records"
    academic_record_id: Mapped[UUID]
    semester: Mapped[int]
    sgpa: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    sgpa_state: Mapped[str] = mapped_column(String(20))
    scale_id: Mapped[UUID | None]
    constraints = (
        scoped_fk("academic_record_id", "student_academic_records"),
        scoped_fk("scale_id", "grading_scales"),
        UniqueConstraint("institution_id", "academic_record_id", "semester"),
        CheckConstraint("semester > 0", name="semester_positive"),
        *mark_constraints("sgpa", "999999"),
        CheckConstraint("sgpa_state != 'KNOWN' OR scale_id IS NOT NULL", name="sgpa_scale"),
    )


class Backlog(TenantRow):
    __tablename__ = "student_backlogs"
    student_id: Mapped[UUID]
    obligation_key: Mapped[str] = mapped_column(String(100))
    constraints = (
        scoped_fk("student_id", "students"),
        UniqueConstraint("institution_id", "student_id", "obligation_key"),
    )


class BacklogEvent(Revision, TenantRow):
    __tablename__ = "student_backlog_events"
    backlog_id: Mapped[UUID]
    kind: Mapped[str] = mapped_column(String(20))
    constraints = (
        *revision_constraints("backlog_id", "student_backlogs"),
        choices("kind", "OPENED CLEARED CORRECTED"),
    )


class Skill(Revision, TenantRow):
    __tablename__ = "student_skills"
    student_id: Mapped[UUID]
    code: Mapped[str] = mapped_column(String(100))
    description: Mapped[str]
    constraints = (
        scoped_fk("student_id", "students"),
        UniqueConstraint("institution_id", "student_id", "code", "version"),
        CheckConstraint("version > 0", name="positive_version"),
    )


class Certification(Revision, TenantRow):
    __tablename__ = "student_certifications"
    student_id: Mapped[UUID]
    credential_key: Mapped[str] = mapped_column(String(100))
    title: Mapped[str]
    constraints = (
        scoped_fk("student_id", "students"),
        UniqueConstraint("institution_id", "student_id", "credential_key", "version"),
        CheckConstraint("version > 0", name="positive_version"),
    )
