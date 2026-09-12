import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy import text
from app.infrastructure.models.students import Institution, User, Role, UserRole, AcademicYear
from app.infrastructure.models.policy import Policy, PolicyVersion, PolicyActivation
from app.infrastructure.repositories.student import StudentRepository
from app.infrastructure.repositories.policy import PolicyRepository, PolicyVersionRepository, PolicyActivationRepository
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

pytestmark = pytest.mark.anyio

@pytest.fixture(scope="session")
def anyio_backend():
    return 'asyncio'

@pytest.fixture(scope="session")
async def db_engine():
    engine = create_async_engine("postgresql+psycopg://test:test@127.0.0.1:5434/test")
    yield engine
    engine.sync_engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest.fixture
async def institution(db_session: AsyncSession):
    inst = Institution(code="AMRITA", name="Amrita Vishwa Vidyapeetham")
    db_session.add(inst)
    await db_session.flush()
    return inst

@pytest.fixture
async def academic_year(db_session: AsyncSession, institution: Institution):
    ay = AcademicYear(
        institution_id=institution.id,
        code="2026-27",
        starts_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
        ends_at=datetime(2027, 6, 30, tzinfo=timezone.utc),
        source_type="SYSTEM",
        source_reference="seed",
    )
    db_session.add(ay)
    await db_session.flush()
    return ay

async def test_synthetic_seed_dataset(db_session: AsyncSession, institution: Institution, academic_year: AcademicYear):
    # This proves we can create complex interrelated records through repositories
    # Student Repository
    repo = StudentRepository(db_session)
    student = await repo.create(
        institution_id=institution.id,
        roll_number="CB.EN.U4CSE23001",
        source_type="SYSTEM",
        source_reference="seed",
        verification="UNVERIFIED",
    )
    assert student.id is not None
    assert student.roll_number == "CB.EN.U4CSE23001"

async def test_constraint_negative_overlapping_policy(db_session: AsyncSession, institution: Institution, academic_year: AcademicYear):
    policy_repo = PolicyRepository(db_session)
    policy = await policy_repo.create(
        institution_id=institution.id,
        code="PLACEMENT_2026",
        name="Placement Policy 2026",
        source_type="SYSTEM",
        source_reference="seed",
    )

    pv_repo = PolicyVersionRepository(db_session)
    pv = await pv_repo.create(
        institution_id=institution.id,
        policy_id=policy.id,
        academic_year_id=academic_year.id,
        scope="BTECH",
        status="APPROVED",
        schema_version=1,
        definition={"rules": []},
        version=1,
        effective_at=datetime.now(timezone.utc),
        source_type="SYSTEM",
        source_reference="seed",
    )

    act_repo = PolicyActivationRepository(db_session)
    t1 = datetime(2026, 8, 1, tzinfo=timezone.utc)
    t2 = datetime(2026, 12, 1, tzinfo=timezone.utc)
    
    await act_repo.create(
        institution_id=institution.id,
        policy_version_id=pv.id,
        academic_year_id=academic_year.id,
        scope="BTECH",
        starts_at=t1,
        ends_at=t2,
        source_type="SYSTEM",
        source_reference="seed",
    )

    # Overlapping activation
    with pytest.raises(IntegrityError) as exc:
        await act_repo.create(
            institution_id=institution.id,
            policy_version_id=pv.id,
            academic_year_id=academic_year.id,
            scope="BTECH",
            starts_at=t1 + timedelta(days=10),
            ends_at=t2 + timedelta(days=10),
            source_type="SYSTEM",
            source_reference="seed",
        )
    assert "ex_policy_activation_overlap" in str(exc.value)

async def test_transaction_rollback(db_session: AsyncSession, institution: Institution):
    repo = StudentRepository(db_session)
    try:
        async with db_session.begin_nested():
            await repo.create(
                institution_id=institution.id,
                roll_number="INVALID_ROLL",
                source_type="SYSTEM",
                source_reference="", # Violates ck_students_source_present (length > 0)
                verification="UNVERIFIED",
            )
    except IntegrityError:
        pass
    
    # Verify no partial state remains
    students = await repo.get_all()
    assert len(students) == 0

async def test_provenance_versioning(db_session: AsyncSession, institution: Institution):
    repo = StudentRepository(db_session)
    student = await repo.create(
        institution_id=institution.id,
        roll_number="CB.EN.U4CSE23002",
        source_type="SYSTEM",
        source_reference="doc_v1",
        verification="UNVERIFIED",
    )
    
    # Update shouldn't accidentally clear source_reference if explicitly tested
    await repo.update(student, verification="VERIFIED")
    
    loaded = await repo.get_by_id(student.id)
    assert loaded.source_reference == "doc_v1"
    assert loaded.verification == "VERIFIED"
