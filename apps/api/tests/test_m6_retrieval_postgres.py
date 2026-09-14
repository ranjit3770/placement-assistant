import uuid
import datetime
import httpx
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.infrastructure.models.policy import Document, Policy, PolicyVersion
from app.infrastructure.models.students import Institution, User, AcademicYear
from app.infrastructure.models.rag import (
    RagBindingEvent,
    RagChunk,
    RagIndexGeneration,
    RagIngestionRun,
    RagPolicySource,
    RagPublishedGeneration,
    RagSourceObject,
)
from app.rag.contracts import EvidenceError, sha256
from app.rag.embedding_provider import HTTPEmbeddingProvider
from app.rag.qdrant_adapter import QdrantAdapter
from app.rag.retrieval_service import RetrievalService

pytestmark = pytest.mark.anyio


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


async def seed_published_generation(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID, RagPublishedGeneration, list[RagChunk]]:
    inst_id = uuid.uuid4()
    user_id = uuid.uuid4()

    inst = Institution(id=inst_id, code=f"inst-{inst_id.hex[:4]}", name="Test Inst")
    session.add(inst)

    user = User(id=user_id, institution_id=inst_id, login=f"{user_id.hex[:8]}@example.invalid", source_type="SYSTEM", source_reference="test")
    session.add(user)
    await session.flush()

    src_hash = sha256(b"source")

    doc = Document(institution_id=inst_id, storage_key="k", filename="Doc", media_type="text/plain", content_hash=src_hash, source_version="1", source_type="SYSTEM", source_reference="test")
    session.add(doc)

    pol = Policy(institution_id=inst_id, code="POL1", name="Pol", source_type="SYSTEM", source_reference="test")
    session.add(pol)
    await session.flush()

    ay = AcademicYear(institution_id=inst_id, code="AY1", starts_at=datetime.datetime.now(datetime.UTC), ends_at=datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365), source_type="SYSTEM", source_reference="test")
    session.add(ay)
    await session.flush()

    pv = PolicyVersion(institution_id=inst_id, policy_id=pol.id, academic_year_id=ay.id, scope="GENERAL", status="APPROVED", schema_version=1, definition={}, version=1, effective_at=datetime.datetime.now(datetime.UTC), source_type="SYSTEM", source_reference="test")
    session.add(pv)
    await session.flush()

    obj = RagSourceObject(
        institution_id=inst_id,
        document_id=doc.id,
        object_key=f"{inst_id.hex}-{doc.id.hex}-{src_hash}",
        byte_length=100,
        source_hash=src_hash,
        source_type="SYSTEM",
        source_reference="test",
    )
    session.add(obj)
    await session.flush()

    bind = RagPolicySource(
        institution_id=inst_id,
        actor_id=user_id,
        source_object_id=obj.id,
        policy_version_id=pv.id,
        revision=1,
        source_hash=src_hash,
        proposal_reason="test",
        request_id=uuid.uuid4(),
        source_type="SYSTEM",
        source_reference="test",
    )
    session.add(bind)
    await session.flush()

    run = RagIngestionRun(
        institution_id=inst_id,
        binding_id=bind.id,
        schema_version=1,
        parser_version="1",
        chunker_version="1",
        embedding_configuration="test",
        status="COMPLETED",
        normalized_artifact_hash=sha256(b"artifact"),
        source_type="SYSTEM",
        source_reference="test",
    )
    session.add(run)
    await session.flush()
    
    # 2 Chunks
    c1 = RagChunk(institution_id=inst_id, run_id=run.id, source_hash=src_hash, artifact_hash=sha256(b"artifact"), chunk_hash=sha256(b"c1"), content="text1", start_offset=0, end_offset=5, ordinal=0, source_type="SYSTEM", source_reference="test")
    c2 = RagChunk(institution_id=inst_id, run_id=run.id, source_hash=src_hash, artifact_hash=sha256(b"artifact"), chunk_hash=sha256(b"c2"), content="text2", start_offset=5, end_offset=10, ordinal=1, source_type="SYSTEM", source_reference="test")
    session.add_all([c1, c2])
    await session.flush()

    gen = RagIndexGeneration(
        institution_id=inst_id,
        run_id=run.id,
        space_id=sha256(b"space"),
        collection_name="rag_c",
        expected_chunk_count=2,
        status="PUBLISHED",
        source_type="SYSTEM",
        source_reference="test",
    )
    session.add(gen)
    await session.flush()

    pub = RagPublishedGeneration(
        institution_id=inst_id,
        binding_id=bind.id,
        generation_id=gen.id,
        published_at=datetime.datetime.now(datetime.UTC),
        source_type="SYSTEM",
        source_reference="test",
    )
    session.add(pub)
    await session.commit()
    
    return inst_id, pv.id, pub, [c1, c2]


async def test_m6_05_a_authorized_retrieval(sessions: "async_sessionmaker[AsyncSession]") -> None:
    """M6-05-A — Authorized retrieval succeeds"""
    async with sessions() as session:
        inst_id, pv_id, pub, chunks = await seed_published_generation(session)
        
        settings = Settings(embedding_provider_url="http://embed", embedding_model="test-model", embedding_dimensions=2)
        mock_http = AsyncMock()
        mock_http.post.return_value = httpx.Response(200, json={
            "data": [{"index": 0, "embedding": [0.1, 0.2]}]
        }, request=httpx.Request("POST", "http://embed"))
        provider = HTTPEmbeddingProvider(settings, http_client=mock_http)
        
        mock_qdrant_http = AsyncMock()
        mock_qdrant_http.post.return_value = httpx.Response(200, json={
            "result": [
                {"id": str(chunks[0].id), "score": 0.95},
                {"id": str(chunks[1].id), "score": 0.85},
            ]
        }, request=httpx.Request("POST", "http://qdrant"))
        qdrant = QdrantAdapter(http_client=mock_qdrant_http)
        
        service = RetrievalService(session, provider, qdrant)
        evidence = await service.retrieve(inst_id, pv_id, "test query")
        
        assert len(evidence) == 2
        assert evidence[0].citation.chunk_hash == chunks[0].chunk_hash
        assert evidence[0].text == "text1"
        assert evidence[0].score == 0.95


async def test_m6_05_b_unauthorized_tenant_or_policy(sessions: "async_sessionmaker[AsyncSession]") -> None:
    """M6-05-B — Missing or invalid context abstains"""
    async with sessions() as session:
        inst_id, pv_id, pub, chunks = await seed_published_generation(session)
        
        settings = Settings(embedding_provider_url="http://embed", embedding_model="test-model", embedding_dimensions=2)
        provider = HTTPEmbeddingProvider(settings, http_client=AsyncMock())
        qdrant = QdrantAdapter(http_client=AsyncMock())
        
        service = RetrievalService(session, provider, qdrant)
        
        # Wrong tenant
        evidence1 = await service.retrieve(uuid.uuid4(), pv_id, "test")
        assert len(evidence1) == 0
        
        # Wrong policy
        evidence2 = await service.retrieve(inst_id, uuid.uuid4(), "test")
        assert len(evidence2) == 0


async def test_m6_05_c_poisoned_index_resilience(sessions: "async_sessionmaker[AsyncSession]") -> None:
    """M6-05-C — Qdrant returns IDs not in DB or wrong generation/tenant"""
    async with sessions() as session:
        inst_id, pv_id, pub, chunks = await seed_published_generation(session)
        
        settings = Settings(embedding_provider_url="http://embed", embedding_model="test-model", embedding_dimensions=2)
        mock_http = AsyncMock()
        mock_http.post.return_value = httpx.Response(200, json={
            "data": [{"index": 0, "embedding": [0.1, 0.2]}]
        }, request=httpx.Request("POST", "http://embed"))
        provider = HTTPEmbeddingProvider(settings, http_client=mock_http)
        
        mock_qdrant_http = AsyncMock()
        # Qdrant returns one valid ID, and one random/poisoned ID
        poisoned_id = uuid.uuid4()
        mock_qdrant_http.post.return_value = httpx.Response(200, json={
            "result": [
                {"id": str(chunks[0].id), "score": 0.95},
                {"id": str(poisoned_id), "score": 0.99},
            ]
        }, request=httpx.Request("POST", "http://qdrant"))
        qdrant = QdrantAdapter(http_client=mock_qdrant_http)
        
        service = RetrievalService(session, provider, qdrant)
        evidence = await service.retrieve(inst_id, pv_id, "test query")
        
        # Service must drop the poisoned ID during PostgreSQL re-validation
        assert len(evidence) == 1
        assert evidence[0].citation.chunk_hash == chunks[0].chunk_hash
