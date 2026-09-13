"""Tests for M6 Increment 3: Durable Ingestion."""

import datetime
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infrastructure.models.policy import Document, Policy, PolicyVersion
from app.infrastructure.models.rag import (
    RagChunk,
    RagPolicySource,
    RagSourceObject,
)
from app.infrastructure.models.students import AcademicYear, Institution, User
from app.rag.contracts import EvidenceError, sha256
from app.rag.ingestion_repository import IngestionRepository

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def sessions():
    import os

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    
    url = os.environ.get("M6_TEST_DATABASE_URL")
    if not url:
        pytest.skip("M6_TEST_DATABASE_URL must point to a migrated disposable database")
    engine = create_async_engine(url)
    try:
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()


async def seed(session: AsyncSession) -> tuple[Institution, User, RagPolicySource]:
    inst = Institution(code=f"m6b-{uuid4().hex[:8]}", name="Synthetic M6 Binding")
    session.add(inst)
    await session.flush()

    user = User(
        institution_id=inst.id,
        login=f"{uuid4().hex}@example.invalid",
        source_type="SYSTEM",
        source_reference="m6-test",
    )
    session.add(user)
    
    ay = AcademicYear(
        institution_id=inst.id,
        code=f"AY_{uuid4().hex[:8]}",
        starts_at=datetime.datetime.now(datetime.UTC),
        ends_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365),
        source_type="SYSTEM",
        source_reference="test",
    )
    session.add(ay)
    await session.flush()

    doc = Document(
        institution_id=inst.id,
        filename="policy.txt",
        storage_key=f"simulated/{uuid4()}",
        media_type="text/plain",
        content_hash=sha256(b"test doc content"),
        source_version="v1",
        source_type="SYSTEM",
        source_reference="test",
    )
    session.add(doc)

    policy = Policy(
        institution_id=inst.id,
        code=f"POL_{uuid4().hex[:8]}",
        name="Policy",
        source_type="SYSTEM",
        source_reference="test",
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
        effective_at=datetime.datetime.now(datetime.UTC),
        source_type="SYSTEM",
        source_reference="test",
    )
    session.add(pv)
    await session.flush()

    source_obj = RagSourceObject(
        institution_id=inst.id,
        document_id=doc.id,
        object_key=f"{inst.id.hex}-{doc.id.hex}-{doc.content_hash}",
        byte_length=16,
        source_hash=doc.content_hash,
        source_type="SYSTEM",
        source_reference="test",
    )
    session.add(source_obj)
    await session.flush()
    await session.commit()
    
    import tempfile
    from pathlib import Path

    from app.core.security import Principal
    from app.rag.binding_service import BindingService
    from app.rag.source_service import SourceService
    from app.rag.source_store import LocalDocumentStore
    
    principal = Principal(institution_id=inst.id, sub=user.id, role="COORDINATOR")
    store = LocalDocumentStore(Path(tempfile.mkdtemp()))
    
    await SourceService(session, store, principal).import_matching_bytes(
        doc.id, b"test doc content"
    )
    await session.commit()
    
    service = BindingService(session, store, principal)
    
    view = await service.propose(doc.id, pv.id, uuid4(), "test")
    await session.commit()
    
    view = await service.approve(view.binding_id, uuid4(), "test")
    await session.commit()
    
    binding = await session.get(RagPolicySource, view.binding_id)
    return inst, user, binding


async def test_m6_03_a_idempotency(sessions: "async_sessionmaker[AsyncSession]") -> None:
    """M6-03-A — Idempotency"""
    async with sessions() as session:
        inst, user, binding = await seed(session)
        repo = IngestionRepository(session, inst.id)
        req_id = uuid4()
        
        # enqueue(binding, same versions) -> same run_id
        run1, job1 = await repo.enqueue_run(
            binding, 1, "p1", "c1", "e1", user.id, req_id
        )
        await session.commit()
        
        run2, job2 = await repo.enqueue_run(
            binding, 1, "p1", "c1", "e1", user.id, req_id
        )
        assert run1.id == run2.id
        assert job1.id == job2.id

        # enqueue(binding, changed parser version) -> new run
        run3, job3 = await repo.enqueue_run(
            binding, 1, "p2", "c1", "e1", user.id, req_id
        )
        assert run1.id != run3.id
        
        # enqueue(binding, changed chunker version) -> new run
        run4, job4 = await repo.enqueue_run(
            binding, 1, "p2", "c2", "e1", user.id, req_id
        )
        assert run3.id != run4.id
        await session.commit()


async def test_m6_03_b_tenant_isolation(sessions: "async_sessionmaker[AsyncSession]") -> None:
    """M6-03-B — Tenant isolation"""
    async with sessions() as session:
        inst1, user1, binding1 = await seed(session)
        inst2, user2, binding2 = await seed(session)
        
        repo1 = IngestionRepository(session, inst1.id)
        repo2 = IngestionRepository(session, inst2.id)
        
        await repo1.enqueue_run(binding1, 1, "p", "c", "e", user1.id, uuid4())
        await session.commit()
        
        # Tenant B cannot acquire Tenant A job
        res = await repo2.acquire_job()
        assert res is None  # no jobs for inst2 yet
        
        with pytest.raises(EvidenceError, match="BINDING_NOT_FOUND"):
            await repo2.enqueue_run(binding1, 1, "p", "c", "e", user1.id, uuid4())
            

async def test_m6_03_c_lease_concurrency(sessions: "async_sessionmaker[AsyncSession]") -> None:
    """M6-03-C — Lease concurrency"""
    # Requires multiple independent sessions to test locks
    async with sessions() as s0:
        inst, user, binding = await seed(s0)
        repo0 = IngestionRepository(s0, inst.id)
        run, job = await repo0.enqueue_run(binding, 1, "p", "c", "e", user.id, uuid4())
        await s0.commit()
    
    # Worker A
    s1 = sessions()
    repo1 = IngestionRepository(s1, inst.id)
    
    # Worker B
    s2 = sessions()
    repo2 = IngestionRepository(s2, inst.id)
    
    # Worker A acquires
    res1 = await repo1.acquire_job(lease_seconds=3600)
    assert res1 is not None
    r1, j1 = res1
    assert j1.status == "RUNNING"
    assert j1.attempt == 1
    
    # Worker B tries to acquire, should be rejected (skip locked means it returns None immediately)
    res2 = await repo2.acquire_job(lease_seconds=3600)
    assert res2 is None
    
    j1_id = j1.id
    # Worker A finishes/fails, but for now let's just rollback A and release lock
    await s1.rollback()
    
    # Now B can acquire
    res2 = await repo2.acquire_job(lease_seconds=3600)
    assert res2 is not None
    r2, j2 = res2
    assert j2.id == j1_id
    assert j2.attempt == 1  # A rolled back, so attempt count wasn't committed!
    await s2.commit()
    await s1.close()
    await s2.close()


async def test_m6_03_d_attempt_exhaustion(sessions: "async_sessionmaker[AsyncSession]") -> None:
    """M6-03-D — Attempt exhaustion"""
    async with sessions() as session:
        inst, user, binding = await seed(session)
        repo = IngestionRepository(session, inst.id)
        run, job = await repo.enqueue_run(binding, 1, "p", "c", "e", user.id, uuid4())
        await session.commit()
        
        # Max attempts is 3
        # Attempt 1
        res = await repo.acquire_job(lease_seconds=0)  # expires instantly
        assert res is not None
        await session.commit()
        
        # Attempt 2
        res = await repo.acquire_job(lease_seconds=0)
        assert res is not None
        await session.commit()
        
        # Attempt 3
        res = await repo.acquire_job(lease_seconds=0)
        assert res is not None
        
        # Fail the job on attempt 3
        await repo.update_job(res[1].id, "FAILED", "TEST_STAGE")
        await session.commit()
        
        # Attempt 4 should fail/return None
        res = await repo.acquire_job(lease_seconds=0)
        assert res is None


async def test_m6_03_e_chunk_integrity(sessions: "async_sessionmaker[AsyncSession]") -> None:
    """M6-03-E — Chunk integrity & M6-03-F Locator integrity"""
    async with sessions() as session:
        inst, user, binding = await seed(session)
        repo = IngestionRepository(session, inst.id)
        run, job = await repo.enqueue_run(binding, 1, "p", "c", "e", user.id, uuid4())
        
        # Must update run's artifact hash so chunk constraint passes
        run.normalized_artifact_hash = sha256(b"artifact")
        run_id_val = run.id
        source_hash_val = binding.source_hash
        artifact_hash_val = run.normalized_artifact_hash
        user_id_val = user.id
        await session.commit()
        
        # Valid chunk
        await repo.save_chunks(
            run_id_val,
            [{
                "ordinal": 0,
                "content": '{"text": "chunk"}',
                "page": 1,
                "section": "Intro",
                "start_offset": 0,
                "end_offset": 10,
                "source_hash": source_hash_val,
                "artifact_hash": artifact_hash_val,
                "chunk_hash": sha256(b"chunk0"),
            }],
            user_id_val,
            uuid4(),
        )
        await session.commit()

        # Invalid source hash
        with pytest.raises(ProgrammingError, match="RAG chunk source hash mismatch"):
            await repo.save_chunks(
                run_id_val,
                [{
                    "ordinal": 1,
                    "content": '{"text": "chunk"}',
                    "page": 1,
                    "section": None,
                    "start_offset": None,
                    "end_offset": None,
                    "source_hash": sha256(b"wrong source"),
                    "artifact_hash": artifact_hash_val,
                    "chunk_hash": sha256(b"chunk1"),
                }],
                user_id_val,
                uuid4(),
            )
            await session.commit()
        await session.rollback()

        # Invalid locator (start > end)
        with pytest.raises(IntegrityError, match="ck_rag_chunks_chunk_offset_bounds"):
            await repo.save_chunks(
                run_id_val,
                [{
                    "ordinal": 2,
                    "content": '{"text": "chunk"}',
                    "page": None,
                    "section": None,
                    "start_offset": 10,
                    "end_offset": 5,
                    "source_hash": source_hash_val,
                    "artifact_hash": artifact_hash_val,
                    "chunk_hash": sha256(b"chunk2"),
                }],
                user_id_val,
                uuid4(),
            )
            await session.commit()
        await session.rollback()


async def test_m6_03_g_partial_ingestion(sessions: "async_sessionmaker[AsyncSession]") -> None:
    """M6-03-G — Partial ingestion semantics"""
    async with sessions() as session:
        inst, user, binding = await seed(session)
        repo = IngestionRepository(session, inst.id)
        run, job = await repo.enqueue_run(binding, 1, "p", "c", "e", user.id, uuid4())
        
        run.normalized_artifact_hash = sha256(b"artifact")
        run_id_val = run.id
        source_hash_val = binding.source_hash
        artifact_hash_val = run.normalized_artifact_hash
        user_id_val = user.id
        await session.commit()
        
        # Save chunk 1
        await repo.save_chunks(
            run_id_val,
            [{
                "ordinal": 0,
                "content": '{"text": "c0"}',
                "page": 1,
                "section": None,
                "start_offset": None,
                "end_offset": None,
                "source_hash": source_hash_val,
                "artifact_hash": artifact_hash_val,
                "chunk_hash": sha256(b"c0"),
            }],
            user_id_val,
            uuid4(),
        )
        
        # Job fails
        await repo.update_job(job.id, "FAILED", "CHUNKING")
        await session.commit()
        
        # Chunk exists, job failed, run failed
        # This confirms that chunk existence does not mean publication.
        # Run state is failed.
        await session.refresh(run)
        assert run.status == "FAILED"
        
        # Chunk still persisted
        sa = pytest.importorskip("sqlalchemy")
        stmt = sa.select(sa.func.count()).select_from(RagChunk).where(RagChunk.run_id == run_id_val)
        chunk_count = await session.scalar(stmt)
        assert chunk_count == 1
