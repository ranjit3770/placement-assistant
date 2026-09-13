"""Run explicitly against a migrated, disposable PostgreSQL database.

M6_TEST_DATABASE_URL is required; there is no production/default DB fallback.
"""

import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import Principal
from app.infrastructure.models.policy import Document, Policy, PolicyVersion
from app.infrastructure.models.students import AcademicYear, Institution, User
from app.rag.binding_service import BindingService, BindingState
from app.rag.contracts import EvidenceError, sha256
from app.rag.source_service import SourceService
from app.rag.source_store import LocalDocumentStore

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def sessions() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    url = os.environ.get("M6_TEST_DATABASE_URL")
    if not url:
        pytest.skip("M6_TEST_DATABASE_URL must point to a migrated disposable database")
    engine = create_async_engine(url)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


async def seed(session: AsyncSession) -> tuple[Principal, Document, PolicyVersion]:
    inst = Institution(code=f"m6b-{uuid4().hex[:8]}", name="Synthetic M6 Binding")
    session.add(inst)
    await session.flush()

    ay = AcademicYear(
        institution_id=inst.id,
        code=f"AY25_M6_{uuid4().hex[:8]}",
        starts_at=datetime.now(UTC) - timedelta(days=30),
        ends_at=datetime.now(UTC) + timedelta(days=365),
        source_type="SYSTEM",
        source_reference="m6-test",
    )
    session.add(ay)
    await session.flush()

    user = User(
        institution_id=inst.id,
        login=f"{uuid4().hex}@example.invalid",
        source_type="SYSTEM",
        source_reference="m6-test",
    )
    session.add(user)
    await session.flush()

    document = Document(
        institution_id=inst.id,
        filename="policy.txt",
        storage_key=f"simulated/{uuid4()}",
        media_type="text/plain",
        content_hash=sha256(b"original\r\n"),
        source_version="v1",
        source_type="SYSTEM",
        source_reference="m6-test",
    )
    session.add(document)

    policy = Policy(
        institution_id=inst.id,
        code=f"POL_{uuid4().hex[:8]}",
        name="Policy",
        source_type="SYSTEM",
        source_reference="m6-test",
    )
    session.add(policy)
    await session.flush()

    pv = PolicyVersion(
        institution_id=inst.id,
        policy_id=policy.id,
        academic_year_id=ay.id,
        scope="DEFAULT",
        status="ACTIVE",
        schema_version=1,
        definition={},
        version=1,
        effective_at=datetime.now(UTC),
        source_type="SYSTEM",
        source_reference="m6-test",
    )
    session.add(pv)
    await session.commit()

    return Principal(institution_id=inst.id, sub=user.id, role="COORDINATOR"), document, pv


async def test_binding_lifecycle(sessions, tmp_path: Path) -> None:
    async with sessions() as session:
        principal, doc, pv = await seed(session)
        store = LocalDocumentStore(tmp_path / "private")

        await SourceService(session, store, principal).import_matching_bytes(
            doc.id, b"original\r\n"
        )
        await session.commit()

        service = BindingService(session, store, principal)
        req_id = uuid4()
        reason = "Initial proposal"

        view = await service.propose(doc.id, pv.id, req_id, reason)
        await session.commit()

        assert view.state == BindingState.PROPOSED
        assert view.revision == 1
        assert view.previous_revision_id is None
        assert len(view.events) == 1
        assert view.events[0].state == BindingState.PROPOSED

        app_req = uuid4()
        view = await service.approve(view.binding_id, app_req, "Looks good")
        await session.commit()

        assert view.state == BindingState.APPROVED
        assert len(view.events) == 2
        assert view.events[-1].state == BindingState.APPROVED

        rev_req = uuid4()
        view = await service.revoke(view.binding_id, rev_req, "Superceded")
        await session.commit()

        assert view.state == BindingState.REVOKED
        assert len(view.events) == 3
        assert view.events[-1].state == BindingState.REVOKED

        req_id2 = uuid4()
        view2 = await service.propose(doc.id, pv.id, req_id2, "New revision")
        await session.commit()

        assert view2.state == BindingState.PROPOSED
        assert view2.revision == 2
        assert view2.previous_revision_id == view.binding_id


async def test_idempotency_and_guard(sessions, tmp_path: Path) -> None:
    async with sessions() as session:
        principal, doc, pv = await seed(session)
        store = LocalDocumentStore(tmp_path / "private")

        await SourceService(session, store, principal).import_matching_bytes(
            doc.id, b"original\r\n"
        )
        await session.commit()

        service = BindingService(session, store, principal)
        req_id = uuid4()

        view1 = await service.propose(doc.id, pv.id, req_id, "Idempotent proposal")
        await session.commit()

        view2 = await service.propose(doc.id, pv.id, req_id, "Idempotent proposal")
        assert view1.binding_id == view2.binding_id

        with pytest.raises(EvidenceError, match="^IDEMPOTENCY_CONFLICT$"):
            await service.propose(doc.id, pv.id, req_id, "Different reason")

        req_id3 = uuid4()
        with pytest.raises(EvidenceError, match="^BINDING_REVISION_STILL_OPEN$"):
            await service.propose(doc.id, pv.id, req_id3, "Cannot propose while open")


async def test_unauthorized_student(sessions, tmp_path: Path) -> None:
    async with sessions() as session:
        principal, doc, pv = await seed(session)
        student_principal = principal.model_copy(update={"role": "STUDENT"})
        store = LocalDocumentStore(tmp_path / "private")

        await SourceService(session, store, principal).import_matching_bytes(
            doc.id, b"original\r\n"
        )
        await session.commit()

        service = BindingService(session, store, student_principal)
        with pytest.raises(EvidenceError, match="^FORBIDDEN$"):
            await service.propose(doc.id, pv.id, uuid4(), "Student proposal")
