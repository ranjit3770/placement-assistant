"""Run explicitly against a migrated, disposable PostgreSQL database.

M6_TEST_DATABASE_URL is required; there is no production/default DB fallback.
"""

import asyncio
import os
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import Principal
from app.infrastructure.models.policy import Document
from app.infrastructure.models.rag import RagSourceObject
from app.infrastructure.models.students import Institution, User
from app.rag.contracts import EvidenceError, SourceIdentity, sha256
from app.rag.source_repository import SourceRepository
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


async def seed(session: AsyncSession) -> tuple[Principal, Document]:
    inst = Institution(code=f"m6-{uuid4().hex}", name="Synthetic M6")
    session.add(inst)
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
    await session.commit()
    return Principal(institution_id=inst.id, sub=user.id, role="COORDINATOR"), document


async def test_matching_import_and_legacy_absence(sessions, tmp_path: Path) -> None:
    async with sessions() as session:
        principal, doc = await seed(session)
        service = SourceService(session, LocalDocumentStore(tmp_path / "private"), principal)
        with pytest.raises(EvidenceError, match="^SOURCE_UNAVAILABLE$"):
            await service.read_for_review(doc.id)
        with pytest.raises(EvidenceError, match="^SOURCE_HASH_MISMATCH$"):
            await service.import_matching_bytes(doc.id, b"original\n")
        assert await service.repository.get(doc.id) is None
        row = await service.import_matching_bytes(doc.id, b"original\r\n")
        await session.commit()
        again = await service.import_matching_bytes(doc.id, b"original\r\n")
        assert again.id == row.id
        assert await service.read_for_review(doc.id) == b"original\r\n"
        await session.refresh(doc)
        assert doc.content_hash == sha256(b"original\r\n")
        assert doc.storage_key.startswith("simulated/"), "Do not rewrite certified metadata"


async def test_cross_tenant_and_student_denial(sessions, tmp_path: Path) -> None:
    async with sessions() as session:
        principal, doc = await seed(session)
        foreign, _ = await seed(session)
        store = LocalDocumentStore(tmp_path / "private")
        with pytest.raises(EvidenceError, match="^SOURCE_NOT_FOUND$"):
            await SourceService(session, store, foreign).import_matching_bytes(
                doc.id, b"original\r\n"
            )
        student = principal.model_copy(update={"role": "STUDENT"})
        with pytest.raises(EvidenceError, match="^FORBIDDEN$"):
            await SourceService(session, store, student).import_matching_bytes(
                doc.id, b"original\r\n"
            )
        with pytest.raises(EvidenceError, match="^FORBIDDEN$"):
            await SourceService(session, store, student).read_for_review(doc.id)
        assert list((tmp_path / "private").iterdir()) == []


@pytest.mark.parametrize("operation", ["update", "delete"])
async def test_database_source_immutability(sessions, tmp_path: Path, operation: str) -> None:
    async with sessions() as session:
        principal, doc = await seed(session)
        document_id = doc.id
        service = SourceService(session, LocalDocumentStore(tmp_path / "private"), principal)
        source = await service.import_matching_bytes(doc.id, b"original\r\n")
        await session.commit()
        statement = (
            update(RagSourceObject).where(RagSourceObject.id == source.id).values(byte_length=1)
            if operation == "update"
            else delete(RagSourceObject).where(RagSourceObject.id == source.id)
        )
        with pytest.raises(DBAPIError, match="Immutable RAG source metadata"):
            await session.execute(statement)
        await session.rollback()
        assert await service.read_for_review(document_id) == b"original\r\n"


@pytest.mark.parametrize("foreign", [False, True])
async def test_database_rejects_hash_or_tenant_forgery(sessions, foreign: bool) -> None:
    async with sessions() as session:
        principal, doc = await seed(session)
        other, _ = await seed(session)
        tenant = other.institution_id if foreign else principal.institution_id
        source_hash = doc.content_hash if foreign else sha256(b"forged")
        identity = SourceIdentity(tenant, doc.id, source_hash)
        session.add(
            RagSourceObject(
                institution_id=tenant,
                document_id=doc.id,
                object_key=identity.object_key,
                source_hash=source_hash,
                byte_length=10,
                source_type="SYSTEM",
                source_reference="test",
            )
        )
        with pytest.raises(DBAPIError, match="RAG source must match tenant document hash"):
            await session.flush()
        await session.rollback()


async def test_concurrent_import_has_one_metadata_row(sessions, tmp_path: Path) -> None:
    async with sessions() as session:
        principal, doc = await seed(session)
    store = LocalDocumentStore(tmp_path / "private")

    async def import_one():
        async with sessions() as session:
            row = await SourceService(session, store, principal).import_matching_bytes(
                doc.id, b"original\r\n"
            )
            await session.commit()
            return row.id

    ids = await asyncio.gather(import_one(), import_one())
    assert ids[0] == ids[1]
    async with sessions() as session:
        count = await session.scalar(
            select(func.count())
            .select_from(RagSourceObject)
            .where(
                RagSourceObject.institution_id == principal.institution_id,
                RagSourceObject.document_id == doc.id,
            )
        )
        assert count == 1


async def test_uncommitted_object_is_not_authorized_metadata(sessions, tmp_path: Path) -> None:
    async with sessions() as session:
        principal, doc = await seed(session)
        document_id = doc.id
        store = LocalDocumentStore(tmp_path / "private")
        service = SourceService(session, store, principal)
        await service.import_matching_bytes(doc.id, b"original\r\n")
        await session.rollback()
        assert await SourceRepository(session, principal.institution_id).get(document_id) is None
        with pytest.raises(EvidenceError, match="^SOURCE_UNAVAILABLE$"):
            await service.read_for_review(document_id)
        # Retry reconciles preserved bytes without requiring an overwrite.
        await service.import_matching_bytes(document_id, b"original\r\n")
        await session.commit()
        assert await service.read_for_review(document_id) == b"original\r\n"
