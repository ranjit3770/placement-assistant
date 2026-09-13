import pytest
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport
from uuid import uuid4
import asyncio

from app.main import create_app
from app.core.config import Settings
from app.core.security import Principal
from app.infrastructure.models.students import Institution, AcademicYear
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

pytestmark = pytest.mark.anyio


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def db_engine():
    engine = create_async_engine("postgresql+psycopg://test:test@127.0.0.1:5434/test")
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    async_session = sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def inst(db_session: AsyncSession):
    inst = Institution(code=f"INST_{uuid4().hex[:8]}", name="Institution API Test")
    db_session.add(inst)
    await db_session.commit()
    await db_session.refresh(inst)
    return inst


@pytest.fixture
async def ay(db_session: AsyncSession, inst):
    from datetime import datetime, timezone, timedelta

    ay = AcademicYear(
        institution_id=inst.id,
        code="AY25",
        starts_at=datetime.now(timezone.utc),
        ends_at=datetime.now(timezone.utc) + timedelta(days=365),
        source_type="SYSTEM",
        source_reference="test",
    )
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

    # We need to override dependencies:
    # 1. db session inside request.state.dependencies
    # 2. current_principal

    from app.core.security import current_principal

    principal = Principal(
        sub=str(uuid4()), user_id=uuid4(), institution_id=inst.id, role="COORDINATOR"
    )
    app.dependency_overrides[current_principal] = lambda: principal

    @app.middleware("http")
    async def override_db_session(request, call_next):
        class MockDeps:
            session = db_session

        request.state.dependencies = MockDeps()
        try:
            return await call_next(request)
        except Exception as e:
            import traceback

            traceback.print_exc()
            raise e

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def test_companies_api(app_client):
    # Create company
    company_code = f"GOOG_{uuid4().hex[:8]}"
    res = await app_client.post("/api/v1/companies", json={"code": company_code, "name": "Google"})
    assert res.status_code == 201
    company_id = res.json()["id"]

    # Update company
    res = await app_client.put(f"/api/v1/companies/{company_id}", json={"name": "Alphabet"})
    assert res.status_code == 200
    assert res.json()["name"] == "Alphabet"

    # Create role
    res = await app_client.post(
        f"/api/v1/companies/{company_id}/roles", json={"code": "SWE", "title": "Software Engineer"}
    )
    assert res.status_code == 201
    role_id = res.json()["id"]


async def test_opportunities_api(app_client, ay):
    # Setup company and role
    company_code = f"MSFT_{uuid4().hex[:8]}"
    res = await app_client.post(
        "/api/v1/companies", json={"code": company_code, "name": "Microsoft"}
    )
    company_id = res.json()["id"]
    res = await app_client.post(
        f"/api/v1/companies/{company_id}/roles", json={"code": "SWE", "title": "Software Engineer"}
    )
    role_id = res.json()["id"]

    # Create drive
    res = await app_client.post(
        f"/api/v1/companies/{company_id}/drives", json={"academic_year_id": str(ay.id)}
    )
    assert res.status_code == 201
    drive_id = res.json()["id"]

    # Create opportunity
    res = await app_client.post(
        f"/api/v1/companies/{company_id}/opportunities",
        json={
            "role_id": role_id,
            "drive_id": drive_id,
        },
    )
    assert res.status_code == 201
    opp_id = res.json()["id"]

    # Close opportunity
    res = await app_client.put(f"/api/v1/opportunities/{opp_id}/close")
    assert res.status_code == 200
    assert res.json()["status"] == "CLOSED"


async def test_requirements_api(app_client, ay):
    # Setup
    company_code = f"AMZN_{uuid4().hex[:8]}"
    res = await app_client.post("/api/v1/companies", json={"code": company_code, "name": "Amazon"})
    company_id = res.json()["id"]
    res = await app_client.post(
        f"/api/v1/companies/{company_id}/roles", json={"code": "SDE1", "title": "Software Dev"}
    )
    role_id = res.json()["id"]
    res = await app_client.post(
        f"/api/v1/companies/{company_id}/drives", json={"academic_year_id": str(ay.id)}
    )
    drive_id = res.json()["id"]
    res = await app_client.post(
        f"/api/v1/companies/{company_id}/opportunities",
        json={
            "role_id": role_id,
            "drive_id": drive_id,
        },
    )
    opp_id = res.json()["id"]

    # 1. Initialize requirement graph
    comp_data = {
        "original_text": "20LPA",
        "currency": "INR",
        "period": "ANNUAL",
        "basis": "TOTAL_CTC",
        "shape": "EXACT",
        "amount": "2000000",
        "comparison_state": "UNRESOLVED",
        "review_reason": "Pending conversion rate confirmation",
    }
    res = await app_client.post(f"/api/v1/opportunities/{opp_id}/requirements", json=comp_data)
    assert res.status_code == 201
    req_v_id = res.json()["id"]

    # 2. Add criterion
    crit_data = {
        "code": "CGPA_ABOVE_8",
        "applicability": "REQUIRED",
        "operator": ">=",
        "operand": {"value": "8.0"},
    }
    res = await app_client.post(
        f"/api/v1/requirements/versions/{req_v_id}/criteria", json=crit_data
    )
    assert res.status_code == 201
    crit_id = res.json()["id"]

    # 3. Add member
    res = await app_client.post(
        f"/api/v1/requirements/criteria/{crit_id}/members", json={"value": "B.Tech CSE"}
    )
    assert res.status_code == 201

    # 4. Publish version
    res = await app_client.post(f"/api/v1/requirements/versions/{req_v_id}/publish")
    assert res.status_code == 200
    assert res.json()["published_at"] is not None

    # 5. Cannot add criterion after publishing
    res = await app_client.post(
        f"/api/v1/requirements/versions/{req_v_id}/criteria", json=crit_data
    )
    assert res.status_code == 400


async def test_tenant_isolation(app_client, db_session, inst, ay):
    from app.infrastructure.models.students import Institution
    from uuid import uuid4
    from app.core.security import current_principal, Principal

    # 1. Create company in Tenant A
    company_code = f"T1_{uuid4().hex[:8]}"
    res = await app_client.post(
        "/api/v1/companies", json={"code": company_code, "name": "Company A"}
    )
    assert res.status_code == 201
    company_id = res.json()["id"]

    # 2. Create Tenant B and switch context
    inst_b = Institution(code=f"INST_B_{uuid4().hex[:8]}", name="Tenant B")
    db_session.add(inst_b)
    await db_session.commit()
    await db_session.refresh(inst_b)

    app = app_client._transport.app
    original_override = app.dependency_overrides.get(current_principal)

    app.dependency_overrides[current_principal] = lambda: Principal(
        sub=str(uuid4()), institution_id=inst_b.id, role="COORDINATOR"
    )

    try:
        # 3. Attempt to GET or PUT Company A from Tenant B
        res = await app_client.put(f"/api/v1/companies/{company_id}", json={"name": "Hacked"})
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "NOT_FOUND"

        # 4. Attempt cross-tenant opportunity creation (Company A)
        res = await app_client.post(
            f"/api/v1/companies/{company_id}/opportunities",
            json={"role_id": str(uuid4()), "drive_id": str(uuid4())},
        )
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "NOT_FOUND"
    finally:
        # Restore context
        if original_override:
            app.dependency_overrides[current_principal] = original_override


async def test_company_revisions(app_client, db_session):
    from sqlalchemy import select
    from app.infrastructure.models.recruitment import CompanyRevision
    from uuid import uuid4

    company_code = f"REV_{uuid4().hex[:8]}"
    res = await app_client.post("/api/v1/companies", json={"code": company_code, "name": "Rev 1"})
    company_id = res.json()["id"]

    await app_client.put(f"/api/v1/companies/{company_id}", json={"name": "Rev 2"})
    await app_client.put(f"/api/v1/companies/{company_id}", json={"name": "Rev 3"})

    # Query database directly
    result = await db_session.execute(
        select(CompanyRevision)
        .where(CompanyRevision.company_id == company_id)
        .order_by(CompanyRevision.version)
    )
    revisions = result.scalars().all()

    assert len(revisions) == 3
    assert revisions[0].version == 1 and revisions[0].name == "Rev 1"
    assert revisions[1].version == 2 and revisions[1].name == "Rev 2"
    assert revisions[2].version == 3 and revisions[2].name == "Rev 3"


async def test_company_role_ownership(app_client, ay):
    from uuid import uuid4

    # Company A
    res = await app_client.post(
        "/api/v1/companies", json={"code": f"CA_{uuid4().hex[:8]}", "name": "Company A"}
    )
    comp_a = res.json()["id"]
    res = await app_client.post(
        f"/api/v1/companies/{comp_a}/roles", json={"code": "R_A", "title": "Role A"}
    )
    role_a = res.json()["id"]

    # Company B
    res = await app_client.post(
        "/api/v1/companies", json={"code": f"CB_{uuid4().hex[:8]}", "name": "Company B"}
    )
    comp_b = res.json()["id"]
    res = await app_client.post(
        f"/api/v1/companies/{comp_b}/roles", json={"code": "R_B", "title": "Role B"}
    )
    role_b = res.json()["id"]

    res = await app_client.post(
        f"/api/v1/companies/{comp_a}/drives", json={"academic_year_id": str(ay.id)}
    )
    drive_a = res.json()["id"]

    # Attempt to use Role B on Company A
    res = await app_client.post(
        f"/api/v1/companies/{comp_a}/opportunities", json={"role_id": role_b, "drive_id": drive_a}
    )

    assert res.status_code == 409
    assert res.json()["error"]["code"] == "CONFLICT"


async def test_opportunity_close_idempotency(app_client, ay):
    from uuid import uuid4

    res = await app_client.post(
        "/api/v1/companies", json={"code": f"LIFE_{uuid4().hex[:8]}", "name": "Life"}
    )
    comp_id = res.json()["id"]
    res = await app_client.post(
        f"/api/v1/companies/{comp_id}/roles", json={"code": "R", "title": "Role"}
    )
    role_id = res.json()["id"]
    res = await app_client.post(
        f"/api/v1/companies/{comp_id}/drives", json={"academic_year_id": str(ay.id)}
    )
    drive_id = res.json()["id"]

    res = await app_client.post(
        f"/api/v1/companies/{comp_id}/opportunities",
        json={"role_id": role_id, "drive_id": drive_id},
    )
    opp_id = res.json()["id"]
    assert res.json()["status"] == "DRAFT"

    # OPEN -> CLOSED (we just use close directly)
    res = await app_client.put(f"/api/v1/opportunities/{opp_id}/close")
    assert res.status_code == 200
    assert res.json()["status"] == "CLOSED"

    # CLOSED -> CLOSED (idempotent)
    res = await app_client.put(f"/api/v1/opportunities/{opp_id}/close")
    assert res.status_code == 200
    assert res.json()["status"] == "CLOSED"


async def test_requirement_transaction_rollback(app_client, db_session, ay):
    from sqlalchemy import select
    from app.infrastructure.models.policy import Requirement, RequirementVersion
    from app.infrastructure.models.recruitment import Compensation
    from uuid import uuid4

    res = await app_client.post(
        "/api/v1/companies", json={"code": f"RB_{uuid4().hex[:8]}", "name": "Rollback"}
    )
    comp_id = res.json()["id"]
    res = await app_client.post(
        f"/api/v1/companies/{comp_id}/roles", json={"code": "R", "title": "Role"}
    )
    role_id = res.json()["id"]
    res = await app_client.post(
        f"/api/v1/companies/{comp_id}/drives", json={"academic_year_id": str(ay.id)}
    )
    drive_id = res.json()["id"]
    res = await app_client.post(
        f"/api/v1/companies/{comp_id}/opportunities",
        json={"role_id": role_id, "drive_id": drive_id},
    )
    opp_id = res.json()["id"]

    # Cause a failure (UNRESOLVED without review_reason -> CHECK constraint violation)
    comp_data = {
        "original_text": "20LPA",
        "currency": "INR",
        "period": "ANNUAL",
        "basis": "TOTAL_CTC",
        "shape": "EXACT",
        "amount": "2000000",
        "comparison_state": "UNRESOLVED",
        # missing review_reason
    }

    res = await app_client.post(f"/api/v1/opportunities/{opp_id}/requirements", json=comp_data)
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "CONFLICT"

    await db_session.rollback()

    # Verify no dangling rows for THIS opportunity
    reqs = (
        (await db_session.execute(select(Requirement).where(Requirement.opportunity_id == opp_id)))
        .scalars()
        .all()
    )
    assert len(reqs) == 0
    # Scope to this opportunity's requirements to avoid counting rows from other tests
    req_vs = (
        (
            await db_session.execute(
                select(RequirementVersion)
                .join(Requirement)
                .where(Requirement.opportunity_id == opp_id)
            )
        )
        .scalars()
        .all()
    )
    assert len(req_vs) == 0


async def test_published_version_mutation_rejection(app_client, ay):
    from uuid import uuid4

    res = await app_client.post(
        "/api/v1/companies", json={"code": f"PUB_{uuid4().hex[:8]}", "name": "Publish"}
    )
    comp_id = res.json()["id"]
    res = await app_client.post(
        f"/api/v1/companies/{comp_id}/roles", json={"code": "R", "title": "Role"}
    )
    role_id = res.json()["id"]
    res = await app_client.post(
        f"/api/v1/companies/{comp_id}/drives", json={"academic_year_id": str(ay.id)}
    )
    drive_id = res.json()["id"]
    res = await app_client.post(
        f"/api/v1/companies/{comp_id}/opportunities",
        json={"role_id": role_id, "drive_id": drive_id},
    )
    opp_id = res.json()["id"]

    comp_data = {
        "original_text": "20LPA",
        "currency": "INR",
        "period": "ANNUAL",
        "basis": "TOTAL_CTC",
        "shape": "EXACT",
        "amount": "2000000",
        "comparison_state": "UNRESOLVED",
        "review_reason": "Pending",
    }
    res = await app_client.post(f"/api/v1/opportunities/{opp_id}/requirements", json=comp_data)
    req_v_id = res.json()["id"]

    # Publish
    res = await app_client.post(f"/api/v1/requirements/versions/{req_v_id}/publish")
    assert res.status_code == 200

    # Attempt mutation (API level or DB level trigger hit)
    crit_data = {
        "code": "CGPA",
        "applicability": "REQUIRED",
        "operator": ">=",
        "operand": {"value": "8.0"},
    }
    res = await app_client.post(
        f"/api/v1/requirements/versions/{req_v_id}/criteria", json=crit_data
    )
    assert res.status_code == 400
