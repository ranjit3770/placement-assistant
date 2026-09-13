import pytest
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from uuid import uuid4
import asyncio
from datetime import datetime, timezone, timedelta

from app.main import create_app
from app.core.config import Settings
from app.core.security import Principal
from app.infrastructure.models.students import Institution, AcademicYear
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

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
async def inst(db_session: AsyncSession):
    inst = Institution(code=f"INST_M4_{uuid4().hex[:8]}", name="Institution API Test M4")
    db_session.add(inst)
    await db_session.commit()
    await db_session.refresh(inst)
    return inst

@pytest.fixture
async def ay(db_session: AsyncSession, inst):
    ay = AcademicYear(institution_id=inst.id, code="AY25_M4", starts_at=datetime.now(timezone.utc), ends_at=datetime.now(timezone.utc) + timedelta(days=365), source_type="SYSTEM", source_reference="test")
    db_session.add(ay)
    await db_session.commit()
    await db_session.refresh(ay)
    return ay

@pytest.fixture
async def app_client(inst, db_session, monkeypatch):
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="postgresql+psycopg://test:test@127.0.0.1:5434/test",
        redis_url="redis://127.0.0.1:1/0",
        qdrant_url="http://127.0.0.1:1",
        jwt_secret="test-only-" + "x" * 40,
        dependency_timeout_seconds=0.1,
    )
    
    app = create_app(settings)

    from app.core.security import current_principal
    from app.infrastructure.models.students import User
    
    principal = Principal(sub=uuid4(), institution_id=inst.id, role="COORDINATOR")
    u = User(id=principal.sub, institution_id=inst.id, login=f"coord_{uuid4().hex[:8]}@test.com", source_type="SYSTEM", source_reference="test")
    db_session.add(u)
    # We must commit it so concurrent transactions (if any) or normal inserts can see the user for FK validation.
    # Actually, flush is enough if we are using the same session.
    await db_session.flush()
    
    app.dependency_overrides[current_principal] = lambda: principal

    @app.middleware("http")
    async def override_db_session(request, call_next):
        class MockDeps:
            session = db_session
        request.state.dependencies = MockDeps()
        try:
            return await call_next(request)
        except Exception as e:
            raise e

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest.fixture
def auth_headers():
    return {}

@pytest.fixture
async def student_client(inst, db_session):
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="postgresql+psycopg://test:test@127.0.0.1:5434/test",
        redis_url="redis://127.0.0.1:1/0",
        qdrant_url="http://127.0.0.1:1",
        jwt_secret="test-only-" + "x" * 40,
        dependency_timeout_seconds=0.1,
    )
    app = create_app(settings)
    from app.core.security import current_principal
    from app.infrastructure.models.students import User
    
    principal = Principal(sub=uuid4(), institution_id=inst.id, role="STUDENT")
    u = User(id=principal.sub, institution_id=inst.id, login=f"student_{uuid4().hex[:8]}@test.com", source_type="SYSTEM", source_reference="test")
    db_session.add(u)
    await db_session.flush()
    
    app.dependency_overrides[current_principal] = lambda: principal

    @app.middleware("http")
    async def override_db_session(request, call_next):
        class MockDeps:
            session = db_session
        request.state.dependencies = MockDeps()
        try:
            return await call_next(request)
        except Exception as e:
            raise e

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

async def test_document_metadata(app_client: AsyncClient, auth_headers: dict[str, str]):
    res = await app_client.post("/api/v1/policies/documents", json={
        "filename": "policy2026.pdf",
        "media_type": "application/pdf",
        "content": "policy text content for simulation"
    }, headers=auth_headers)
    if res.status_code != 201:
        print(f"Error: {res.json()}")
    assert res.status_code == 201
    data = res.json()
    assert "content_hash" in data
    assert data["filename"] == "policy2026.pdf"
    assert data["storage_key"].startswith("policies/")

async def test_policy_creation_and_lifecycle(
    app_client: AsyncClient, student_client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession, ay
):
    ay_id = str(ay.id)

    # Create Policy
    res = await app_client.post("/api/v1/policies", json={
        "code": "PLACEMENT-2026",
        "name": "Placement Rules 2026"
    }, headers=auth_headers)
    assert res.status_code == 201
    policy_id = res.json()["id"]

    # Create Policy Version
    res = await app_client.post(f"/api/v1/policies/{policy_id}/versions", json={
        "academic_year_id": ay_id,
        "scope": "ALL",
        "definition": {"summary": "Initial draft"}
    }, headers=auth_headers)
    assert res.status_code == 201
    version_id = res.json()["id"]
    assert res.json()["status"] == "DRAFT"

    # Add Rule in DRAFT
    res = await app_client.post(f"/api/v1/policies/versions/{version_id}/rules", json={
        "code": "CGPA_REQ",
        "definition": {"min_cgpa": 7.0}
    }, headers=auth_headers)
    assert res.status_code == 201

    # Invalid Transition (DRAFT -> REVIEW)
    res = await app_client.post(f"/api/v1/policies/versions/{version_id}/review", json={
        "reason": "Skip processing"
    }, headers=auth_headers)
    assert res.status_code == 400

    # Valid Transition (DRAFT -> PROCESSING)
    res = await app_client.post(f"/api/v1/policies/versions/{version_id}/processing", json={
        "reason": "Start processing"
    }, headers=auth_headers)
    assert res.status_code == 200

    # Add Rule in PROCESSING
    res = await app_client.post(f"/api/v1/policies/versions/{version_id}/rules", json={
        "code": "BACKLOG_REQ",
        "definition": {"max_backlogs": 0}
    }, headers=auth_headers)
    assert res.status_code == 201

    # Transition to REVIEW
    res = await app_client.post(f"/api/v1/policies/versions/{version_id}/review", json={
        "reason": "Ready for review"
    }, headers=auth_headers)
    assert res.status_code == 200

    # Add Rule in REVIEW (Should Fail)
    res = await app_client.post(f"/api/v1/policies/versions/{version_id}/rules", json={
        "code": "INVALID_RULE",
        "definition": {}
    }, headers=auth_headers)
    assert res.status_code == 400

    # Authorization Check: Student cannot approve
    res = await student_client.post(f"/api/v1/policies/versions/{version_id}/approve", json={
        "reason": "Student trying to approve"
    })
    assert res.status_code == 403

    # Authorized Approval
    res = await app_client.post(f"/api/v1/policies/versions/{version_id}/approve", json={
        "reason": "Looks good"
    }, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "APPROVED"

    # Activation
    now = datetime.now(timezone.utc)
    res = await app_client.post(f"/api/v1/policies/versions/{version_id}/activate", json={
        "reason": "Starting year",
        "starts_at": now.isoformat(),
        "ends_at": (now + timedelta(days=365)).isoformat()
    }, headers=auth_headers)
    assert res.status_code == 201
    
    # Try creating another active version for the same year and scope with overlapping dates
    res = await app_client.post(f"/api/v1/policies/{policy_id}/versions", json={
        "academic_year_id": ay_id,
        "scope": "ALL",
        "definition": {"summary": "Second version"}
    }, headers=auth_headers)
    v2_id = res.json()["id"]
    
    await app_client.post(f"/api/v1/policies/versions/{v2_id}/processing", json={"reason": "1"}, headers=auth_headers)
    await app_client.post(f"/api/v1/policies/versions/{v2_id}/review", json={"reason": "2"}, headers=auth_headers)
    await app_client.post(f"/api/v1/policies/versions/{v2_id}/approve", json={"reason": "3"}, headers=auth_headers)
    
    async with db_session.begin_nested():
        res = await app_client.post(f"/api/v1/policies/versions/{v2_id}/activate", json={
            "reason": "Overlap",
            "starts_at": (now + timedelta(days=10)).isoformat(),
            "ends_at": (now + timedelta(days=400)).isoformat()
        }, headers=auth_headers)
    
    # Exclude constraint violation -> IntegrityError -> 409
    assert res.status_code == 409

    # Archive original
    res = await app_client.post(f"/api/v1/policies/versions/{version_id}/archive", json={
        "reason": "End of year"
    }, headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "ARCHIVED"

async def test_concurrent_policy_activation(db_engine):
    import asyncio
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.exc import IntegrityError
    from app.infrastructure.models.policy import Policy, PolicyVersion, PolicyActivation
    from app.infrastructure.models.students import Institution, AcademicYear
    
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False)
    
    async with async_session() as setup_session:
        inst = Institution(code=f"INST_P_{uuid4().hex[:8]}", name="Institution P")
        setup_session.add(inst)
        await setup_session.flush()
        
        ay = AcademicYear(
            institution_id=inst.id, code="2026",
            starts_at=datetime(2026, 7, 1, tzinfo=timezone.utc),
            ends_at=datetime(2027, 6, 30, tzinfo=timezone.utc),
            source_type="SYSTEM", source_reference="seed"
        )
        p = Policy(institution_id=inst.id, code="POL1", name="Policy 1", source_type="SYSTEM", source_reference="seed")
        setup_session.add_all([ay, p])
        await setup_session.flush()
        
        v1 = PolicyVersion(
            institution_id=inst.id, policy_id=p.id, version=1, academic_year_id=ay.id,
            scope="ALL", status="APPROVED", schema_version=1, definition={}, effective_at=datetime.now(timezone.utc),
            source_type="SYSTEM", source_reference="seed"
        )
        v2 = PolicyVersion(
            institution_id=inst.id, policy_id=p.id, version=2, academic_year_id=ay.id,
            scope="ALL", status="APPROVED", schema_version=1, definition={}, effective_at=datetime.now(timezone.utc),
            source_type="SYSTEM", source_reference="seed"
        )
        setup_session.add_all([v1, v2])
        await setup_session.commit()
        
        inst_id = inst.id
        ay_id = ay.id
        v1_id = v1.id
        v2_id = v2.id
        
    async def activate_version(v_id):
        async with async_session() as session:
            act = PolicyActivation(
                institution_id=inst_id,
                policy_version_id=v_id,
                academic_year_id=ay_id,
                scope="ALL",
                starts_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
                ends_at=datetime(2027, 5, 31, tzinfo=timezone.utc),
                source_type="SYSTEM",
                source_reference="seed"
            )
            session.add(act)
            await session.commit()
            
    results = await asyncio.gather(activate_version(v1_id), activate_version(v2_id), return_exceptions=True)
    
    successes = 0
    failures = 0
    for res in results:
        if isinstance(res, Exception):
            assert "ex_policy_activation_overlap" in str(res)
            failures += 1
        else:
            successes += 1
            
    assert successes == 1
    assert failures == 1

