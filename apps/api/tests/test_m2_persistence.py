import asyncio
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy.exc import IntegrityError, ProgrammingError, InternalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.infrastructure.models.students import Institution, AcademicYear, Student, Backlog, BacklogEvent
from app.infrastructure.models.recruitment import Company, Drive, ActiveDreamApproval, DreamDeclaration, DreamEvent
from app.infrastructure.models.policy import Policy, PolicyVersion, PolicyActivation, PolicyRule, Requirement, RequirementVersion, Criterion, RequirementMember
from app.infrastructure.repositories.student import StudentRepository, BacklogEventRepository
from app.infrastructure.repositories.policy import PolicyRepository, PolicyVersionRepository, PolicyActivationRepository
from app.infrastructure.repositories.recruitment import CompanyRepository

# M2 FINAL SYNCHRONIZATION

pytestmark = pytest.mark.anyio

@pytest.fixture(scope="session")
def anyio_backend():
    return 'asyncio'

@pytest.fixture(scope="session")
async def db_engine():
    engine = create_async_engine("postgresql+psycopg://test:test@127.0.0.1:5434/test")
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def inst_a(db_session: AsyncSession):
    inst = Institution(code=f"INST_A_{uuid4().hex[:8]}", name="Institution A")
    db_session.add(inst)
    await db_session.flush()
    return inst

@pytest.fixture
async def inst_b(db_session: AsyncSession):
    inst = Institution(code=f"INST_B_{uuid4().hex[:8]}", name="Institution B")
    db_session.add(inst)
    await db_session.flush()
    return inst

@pytest.fixture
async def ay_a(db_session: AsyncSession, inst_a: Institution):
    ay = AcademicYear(
        institution_id=inst_a.id, code=f"2026_{uuid4().hex[:4]}",
        starts_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        ends_at=datetime(2027, 6, 30, tzinfo=timezone.utc),
        source_type="SYSTEM", source_reference="seed"
    )
    db_session.add(ay)
    await db_session.flush()
    return ay

async def test_tenant_isolation_reads(db_session: AsyncSession, inst_a: Institution, inst_b: Institution):
    repo_a = StudentRepository(db_session, inst_a.id)
    student_a = await repo_a.create(roll_number="A1", source_type="SYSTEM", source_reference="seed")
    
    repo_b = StudentRepository(db_session, inst_b.id)
    student_b = await repo_b.create(roll_number="B1", source_type="SYSTEM", source_reference="seed")
    
    result = await repo_a.get_by_id(student_b.id)
    assert result is None, "Tenant isolation failure"

async def test_append_only_event_protection(db_session: AsyncSession, inst_a: Institution):
    student_repo = StudentRepository(db_session, inst_a.id)
    student = await student_repo.create(roll_number="A2", source_type="SYSTEM", source_reference="seed")
    
    backlog = Backlog(institution_id=inst_a.id, student_id=student.id, obligation_key="MAT101", source_type="SYSTEM", source_reference="seed")
    db_session.add(backlog)
    await db_session.flush()

    event_repo = BacklogEventRepository(db_session, inst_a.id)
    event = await event_repo.append(backlog_id=backlog.id, kind="OPENED", version=1, effective_at=datetime.now(timezone.utc), source_type="SYSTEM", source_reference="seed")
    
    with pytest.raises(ProgrammingError) as exc:
        event.kind = "CLEARED"
        db_session.add(event)
        await db_session.flush()
    assert "Immutable event history" in str(exc.value)

async def test_active_definition_immutability(db_session: AsyncSession, inst_a: Institution, ay_a: AcademicYear):
    inst_id = inst_a.id
    ay_id = ay_a.id
    repo = PolicyVersionRepository(db_session, inst_id)
    policy = Policy(institution_id=inst_id, code="P1", name="Pol", source_type="SYSTEM", source_reference="seed")
    db_session.add(policy)
    await db_session.commit()
    policy_id = policy.id
    
    pv = await repo.create_version(
        policy_id=policy_id, academic_year_id=ay_id, scope="ALL",
        schema_version=1, definition={"rules": []}, version=1, effective_at=datetime.now(timezone.utc),
        source_type="SYSTEM", source_reference="seed", status="APPROVED"
    )
    await db_session.commit()
    pv_id = pv.id
    
    with pytest.raises(ProgrammingError) as exc:
        pv.definition = {"rules": ["changed"]}
        await db_session.flush()
    assert "Immutable definition" in str(exc.value)
    
    await db_session.rollback()
    
    rule = PolicyRule(institution_id=inst_id, policy_version_id=pv_id, code="R1", definition={"x": 1}, source_type="SYSTEM", source_reference="seed")
    db_session.add(rule)
    with pytest.raises(ProgrammingError) as exc:
        await db_session.flush()
    assert "Immutable definition" in str(exc.value)
    
    await db_session.rollback()
    
    # Verify that a DRAFT policy version CAN have rules added
    pv_draft = await repo.create_version(
        policy_id=policy_id, academic_year_id=ay_id, scope="ALL",
        schema_version=1, definition={"rules": []}, version=2, effective_at=datetime.now(timezone.utc),
        source_type="SYSTEM", source_reference="seed", status="DRAFT"
    )
    await db_session.commit()
    pv_draft_id = pv_draft.id
    
    rule_draft = PolicyRule(institution_id=inst_id, policy_version_id=pv_draft_id, code="R2", definition={"x": 2}, source_type="SYSTEM", source_reference="seed")
    db_session.add(rule_draft)
    await db_session.flush()
    
    # Updating a rule in DRAFT is allowed
    rule_draft.definition = {"x": 3}
    await db_session.flush()
    
    # Transitioning to APPROVED is allowed
    # Actually, we didn't rollback since creation of pv_draft, so we can just use pv_draft, but wait, we need to make sure we don't hit MissingGreenlet on pv_draft.status
    pv_draft.status = "APPROVED"
    await db_session.flush()
    
    # Now it is immutable
    rule_draft.definition = {"x": 4}
    with pytest.raises(ProgrammingError) as exc:
        await db_session.flush()
    assert "Immutable definition" in str(exc.value)
    
    await db_session.rollback()

async def test_published_requirement_immutability(db_session: AsyncSession, inst_a: Institution, ay_a: AcademicYear):
    # Setup full opportunity structure
    from app.infrastructure.models.recruitment import CompanyRole
    from app.infrastructure.models.recruitment import Compensation
    from app.infrastructure.models.recruitment import Opportunity
    c = Company(institution_id=inst_a.id, code="C1", source_type="SYSTEM", source_reference="seed")
    db_session.add(c)
    await db_session.flush()
    
    role = CompanyRole(institution_id=inst_a.id, company_id=c.id, code="R1", title="R1", source_type="SYSTEM", source_reference="seed")
    drive = Drive(institution_id=inst_a.id, company_id=c.id, academic_year_id=ay_a.id, source_type="SYSTEM", source_reference="seed")
    db_session.add_all([role, drive])
    await db_session.flush()
    
    opp = Opportunity(institution_id=inst_a.id, company_id=c.id, role_id=role.id, drive_id=drive.id, source_type="SYSTEM", source_reference="seed")
    comp = Compensation(institution_id=inst_a.id, original_text="x", currency="INR", period="ANNUAL", basis="TOTAL_CTC", shape="UNKNOWN", comparison_state="UNRESOLVED", review_reason="missing", source_type="SYSTEM", source_reference="seed")
    db_session.add_all([opp, comp])
    await db_session.flush()

    req = Requirement(institution_id=inst_a.id, opportunity_id=opp.id, source_type="SYSTEM", source_reference="seed")
    db_session.add(req)
    await db_session.commit()
    
    # Published requirement
    req_v = RequirementVersion(
        institution_id=inst_a.id, requirement_id=req.id, compensation_id=comp.id,
        version=1, effective_at=datetime.now(timezone.utc), published_at=datetime.now(timezone.utc),
        source_type="SYSTEM", source_reference="seed"
    )
    db_session.add(req_v)
    await db_session.commit()
    
    criterion = Criterion(
        institution_id=inst_a.id, requirement_version_id=req_v.id, code="C1",
        applicability="REQUIRED", operator=">=", operand={"val": 7.0},
        source_type="SYSTEM", source_reference="seed"
    )
    db_session.add(criterion)
    with pytest.raises(ProgrammingError) as exc:
        await db_session.flush()
    assert "Immutable definition" in str(exc.value)
    
    await db_session.rollback()

async def test_concurrent_dream_approval_limit(db_engine):
    # Setup data in a committed transaction so concurrent sessions can see it
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
    
    async with async_session() as setup_session:
        inst = Institution(code=f"INST_C_{uuid4().hex[:8]}", name="Institution C")
        setup_session.add(inst)
        await setup_session.flush()
        
        ay = AcademicYear(
            institution_id=inst.id, code="2026",
            starts_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
            ends_at=datetime(2027, 6, 30, tzinfo=timezone.utc),
            source_type="SYSTEM", source_reference="seed"
        )
        student = Student(institution_id=inst.id, roll_number="DREAM_STD", source_type="SYSTEM", source_reference="seed")
        c1 = Company(institution_id=inst.id, code="C1", source_type="SYSTEM", source_reference="seed")
        c2 = Company(institution_id=inst.id, code="C2", source_type="SYSTEM", source_reference="seed")
        setup_session.add_all([ay, student, c1, c2])
        await setup_session.flush()
        
        d1 = DreamDeclaration(institution_id=inst.id, student_id=student.id, company_id=c1.id, academic_year_id=ay.id, source_type="SYSTEM", source_reference="seed")
        d2 = DreamDeclaration(institution_id=inst.id, student_id=student.id, company_id=c2.id, academic_year_id=ay.id, source_type="SYSTEM", source_reference="seed")
        setup_session.add_all([d1, d2])
        await setup_session.commit()
        
        inst_id = inst.id
        student_id = student.id
        ay_id = ay.id
        decl1_id = d1.id
        decl2_id = d2.id
    
    async def approve_dream(decl_id):
        async with async_session() as session:
            approval = ActiveDreamApproval(
                institution_id=inst_id,
                student_id=student_id,
                academic_year_id=ay_id,
                declaration_id=decl_id,
                source_type="SYSTEM",
                source_reference="seed"
            )
            session.add(approval)
            await session.commit()
            return True

    results = await asyncio.gather(
        approve_dream(decl1_id),
        approve_dream(decl2_id),
        return_exceptions=True
    )
    
    successes = [r for r in results if r is True]
    errors = [r for r in results if isinstance(r, IntegrityError)]
    
    assert len(successes) == 1, "Exactly one transaction should succeed"
    assert len(errors) == 1, "Exactly one transaction should fail"
    assert "active_dream_approvals" in str(errors[0])
