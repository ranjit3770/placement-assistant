import uuid
import datetime
import httpx
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings
from app.infrastructure.models.policy import Document, Policy, PolicyVersion
from app.infrastructure.models.rag import (
    RagBindingEvent,
    RagChunk,
    RagIndexGeneration,
    RagIngestionRun,
    RagPolicySource,
    RagPublishedGeneration,
    RagSourceObject,
)
from app.rag.contracts import EvidenceError, ManifestPoint, sha256
from app.rag.embedding_provider import HTTPEmbeddingProvider
from app.rag.generation_service import GenerationService
from app.rag.qdrant_adapter import QdrantAdapter

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


from app.infrastructure.models.students import Institution, User, AcademicYear

async def seed_chunks(session: AsyncSession) -> tuple[uuid.UUID, RagIngestionRun, RagPolicySource, uuid.UUID]:
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
        source_object_id=obj.id,
        policy_version_id=pv.id,
        revision=1,
        source_hash=src_hash,
        proposal_reason="test",
        request_id=uuid.uuid4(),
        actor_id=user_id,
        source_type="SYSTEM",
        source_reference="test",
    )
    session.add(bind)
    await session.flush()

    run = RagIngestionRun(
        institution_id=inst_id,
        binding_id=bind.id,
        schema_version=1,
        parser_version="p",
        chunker_version="c",
        embedding_configuration="e",
        status="COMPLETED",
        normalized_artifact_hash=sha256(b"artifact"),
        source_type="SYSTEM",
        source_reference="test",
    )
    session.add(run)
    await session.flush()

    c1 = RagChunk(
        institution_id=inst_id,
        run_id=run.id,
        ordinal=0,
        content='{"text": "c0"}',
        page=1,
        start_offset=0,
        end_offset=10,
        source_hash=src_hash,
        artifact_hash=run.normalized_artifact_hash,
        chunk_hash=sha256(b"c0"),
        source_type="SYSTEM",
        source_reference="test",
    )
    c2 = RagChunk(
        institution_id=inst_id,
        run_id=run.id,
        ordinal=1,
        content='{"text": "c1"}',
        page=1,
        start_offset=10,
        end_offset=20,
        source_hash=src_hash,
        artifact_hash=run.normalized_artifact_hash,
        chunk_hash=sha256(b"c1"),
        source_type="SYSTEM",
        source_reference="test",
    )
    session.add_all([c1, c2])
    await session.commit()
    
    return inst_id, run, bind, user_id


async def test_m6_04_a_embedding_abstraction() -> None:
    """M6-04-A — Embedding abstraction"""
    settings = Settings(embedding_provider_url="http://embed", embedding_model="test-model", embedding_api_key="secret")
    
    # Mock HTTpx Client
    mock_client = AsyncMock()
    mock_client.post.return_value = httpx.Response(200, json={
        "data": [
            {"index": 0, "embedding": [0.1, 0.2]},
            {"index": 1, "embedding": [0.3, 0.4]}
        ]
    }, request=httpx.Request("POST", "http://embed"))
    
    provider = HTTPEmbeddingProvider(settings, http_client=mock_client)
    assert provider.space.dimensions == 1536  # Default fallback
    assert provider.space.model == "test-model"
    
    vectors = await provider.embed(["t1", "t2"])
    assert len(vectors) == 2
    assert vectors[0] == [0.1, 0.2]


async def test_m6_04_b_qdrant_adapter() -> None:
    """M6-04-B — Qdrant Adapter"""
    mock_client = AsyncMock()
    
    # Ensure collection success
    mock_resp_404 = MagicMock()
    mock_resp_404.status_code = 404
    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    
    mock_client.get.return_value = mock_resp_404
    mock_client.put.return_value = mock_resp_200
    
    qdrant = QdrantAdapter(http_client=mock_client)
    await qdrant.ensure_collection("test_col", 1536, "cosine")
    
    mock_client.get.assert_called_with("/collections/test_col")
    mock_client.put.assert_called_with("/collections/test_col", json={"vectors": {"size": 1536, "distance": "Cosine"}})
    
    # Upsert points
    points = [{"id": str(uuid.uuid4()), "vector": [0.1], "payload": {}}]
    await qdrant.upsert_points("test_col", points)
    mock_client.put.assert_called_with("/collections/test_col/points?wait=true", json={"points": points})


async def test_m6_04_c_manifest_verification(sessions: "async_sessionmaker[AsyncSession]") -> None:
    """M6-04-C — Manifest verification"""
    async with sessions() as session:
        inst_id, run, bind, _ = await seed_chunks(session)
        
        settings = Settings(embedding_provider_url="http://embed", embedding_model="test-model", embedding_dimensions=2)
        mock_http = AsyncMock()
        mock_http.post.return_value = httpx.Response(200, json={
            "data": [{"index": 0, "embedding": [0.1, 0.2]}, {"index": 1, "embedding": [0.3, 0.4]}]
        }, request=httpx.Request("POST", "http://embed"))
        provider = HTTPEmbeddingProvider(settings, http_client=mock_http)
        
        mock_qdrant_http = AsyncMock()
        mock_qdrant_http.put.return_value = httpx.Response(200, request=httpx.Request("PUT", "http://qdrant"))
        qdrant = QdrantAdapter(http_client=mock_qdrant_http)
        
        service = GenerationService(session, inst_id, provider, qdrant)
        
        # Test missing point (Qdrant returns 1 point but expected 2)
        mock_qdrant_http.post.return_value = httpx.Response(200, json={
            "result": {
                "points": [
                    {
                        "id": "00000000-0000-0000-0000-000000000000",
                        "payload": {"chunk_hash": sha256(b"c0")}
                    }
                ],
                "next_page_offset": None
            }
        }, request=httpx.Request("POST", "http://qdrant"))
        
        with pytest.raises(EvidenceError, match="MANIFEST_VERIFICATION_FAILED"):
            await service.generate_index(run.id)


async def test_m6_04_d_atomic_publication(sessions: "async_sessionmaker[AsyncSession]") -> None:
    """M6-04-D — Atomic publication"""
    async with sessions() as session:
        inst_id, run, bind, _ = await seed_chunks(session)
        
        settings = Settings(embedding_provider_url="http://embed", embedding_model="test-model", embedding_dimensions=2)
        mock_http = AsyncMock()
        mock_http.post.return_value = httpx.Response(200, json={
            "data": [{"index": 0, "embedding": [0.1, 0.2]}, {"index": 1, "embedding": [0.3, 0.4]}]
        }, request=httpx.Request("POST", "http://embed"))
        provider = HTTPEmbeddingProvider(settings, http_client=mock_http)
        
        # Correct manifest
        # We need the exact deterministic IDs
        space_id = provider.space.space_id
        h1 = sha256(b"c0")
        h2 = sha256(b"c1")
        id1 = str(uuid.UUID(sha256(f"{space_id}:{h1}".encode("utf-8"))[:32]))
        id2 = str(uuid.UUID(sha256(f"{space_id}:{h2}".encode("utf-8"))[:32]))

        mock_qdrant_http = AsyncMock()
        mock_qdrant_http.put.return_value = httpx.Response(200, request=httpx.Request("PUT", "http://qdrant"))
        mock_qdrant_http.post.return_value = httpx.Response(200, json={
            "result": {
                "points": [
                    {"id": id1, "payload": {"chunk_hash": h1}},
                    {"id": id2, "payload": {"chunk_hash": h2}},
                ],
                "next_page_offset": None
            }
        }, request=httpx.Request("POST", "http://qdrant"))
        qdrant = QdrantAdapter(http_client=mock_qdrant_http)
        
        service = GenerationService(session, inst_id, provider, qdrant)
        gen_id = await service.generate_index(run.id)
        
        # Verify it is published
        await session.rollback()
        gen = await session.scalar(select(RagIndexGeneration).where(RagIndexGeneration.id == gen_id))
        assert gen.status == "PUBLISHED"
        
        pub = await session.scalar(select(RagPublishedGeneration).where(RagPublishedGeneration.generation_id == gen_id))
        assert pub is not None


async def test_m6_04_e_partial_failure(sessions: "async_sessionmaker[AsyncSession]") -> None:
    """M6-04-E — Qdrant partial failure"""
    async with sessions() as session:
        inst_id, run, bind, _ = await seed_chunks(session)
        
        settings = Settings(embedding_provider_url="http://embed", embedding_model="test-model", embedding_dimensions=2)
        mock_http = AsyncMock()
        mock_http.post.return_value = httpx.Response(200, json={
            "data": [{"index": 0, "embedding": [0.1, 0.2]}, {"index": 1, "embedding": [0.3, 0.4]}]
        }, request=httpx.Request("POST", "http://embed"))
        provider = HTTPEmbeddingProvider(settings, http_client=mock_http)
        
        mock_qdrant_http = AsyncMock()
        # Fail the upsert
        mock_qdrant_http.put.side_effect = httpx.HTTPError("Network failure")
        qdrant = QdrantAdapter(http_client=mock_qdrant_http)
        
        service = GenerationService(session, inst_id, provider, qdrant)
        
        with pytest.raises(EvidenceError, match="QDRANT_UPSERT_FAILED"):
            await service.generate_index(run.id)
            
        await session.rollback()
        gen = await session.scalar(select(RagIndexGeneration).where(RagIndexGeneration.run_id == run.id))
        assert gen.status == "FAILED"
        
        # Never published
        pub = await session.scalar(select(RagPublishedGeneration).where(RagPublishedGeneration.binding_id == bind.id))
        assert pub is None


async def test_m6_04_f_retry_idempotency(sessions: "async_sessionmaker[AsyncSession]") -> None:
    """M6-04-F — Retry idempotency"""
    async with sessions() as session:
        inst_id, run, bind, _ = await seed_chunks(session)
        
        settings = Settings(embedding_provider_url="http://embed", embedding_model="test-model", embedding_dimensions=2)
        mock_http = AsyncMock()
        mock_http.post.return_value = httpx.Response(200, json={
            "data": [{"index": 0, "embedding": [0.1, 0.2]}, {"index": 1, "embedding": [0.3, 0.4]}]
        }, request=httpx.Request("POST", "http://embed"))
        provider = HTTPEmbeddingProvider(settings, http_client=mock_http)
        
        mock_qdrant_http = AsyncMock()
        # Fail first time
        mock_qdrant_http.put.side_effect = httpx.HTTPError("Network failure")
        qdrant = QdrantAdapter(http_client=mock_qdrant_http)
        
        service = GenerationService(session, inst_id, provider, qdrant)
        
        with pytest.raises(EvidenceError):
            await service.generate_index(run.id)
            
        await session.rollback()
        
        # Recover mock
        mock_qdrant_http.put.side_effect = None
        mock_qdrant_http.put.return_value = httpx.Response(200, request=httpx.Request("PUT", "http://qdrant"))
        space_id = provider.space.space_id
        h1 = sha256(b"c0")
        h2 = sha256(b"c1")
        id1 = str(uuid.UUID(sha256(f"{space_id}:{h1}".encode("utf-8"))[:32]))
        id2 = str(uuid.UUID(sha256(f"{space_id}:{h2}".encode("utf-8"))[:32]))

        mock_qdrant_http.post.return_value = httpx.Response(200, json={
            "result": {
                "points": [
                    {"id": id1, "payload": {"chunk_hash": h1}},
                    {"id": id2, "payload": {"chunk_hash": h2}},
                ],
                "next_page_offset": None
            }
        }, request=httpx.Request("POST", "http://qdrant"))
        
        # Retry
        gen_id = await service.generate_index(run.id)
        
        await session.rollback()
        gen = await session.scalar(select(RagIndexGeneration).where(RagIndexGeneration.id == gen_id))
        assert gen.status == "PUBLISHED"
