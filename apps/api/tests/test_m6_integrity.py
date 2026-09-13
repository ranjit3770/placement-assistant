"""Offline integrity tests, not semantic retrieval or M6 certification."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest

from app.rag.contracts import (
    MAX_SOURCE_BYTES,
    BindingState,
    Chunk,
    EmbeddingSpace,
    EvidenceError,
    ManifestPoint,
    SourceIdentity,
    sha256,
    validate_binding_transition,
    validate_manifest,
    validate_vectors,
)
from app.rag.source_store import LocalDocumentStore


def identity(data: bytes) -> SourceIdentity:
    return SourceIdentity(uuid4(), uuid4(), sha256(data))


@pytest.fixture
def store(tmp_path: Path) -> LocalDocumentStore:
    return LocalDocumentStore(tmp_path / "private")


@pytest.mark.parametrize("data", [b"%PDF-1.7\r\n", "# Policy\r\n₹5 LPA".encode(), b"Text\r\n"])
def test_preserves_original_bytes(store: LocalDocumentStore, data: bytes) -> None:
    source = identity(data)
    store.preserve(source, data)
    assert store.read_verified(source) == data
    assert source.source_hash == sha256(data)


def test_missing_legacy_source_is_unavailable(store: LocalDocumentStore) -> None:
    with pytest.raises(EvidenceError, match="^SOURCE_UNAVAILABLE$"):
        store.read_verified(identity(b"legacy metadata only"))


def test_hash_mismatch_never_creates_object(store: LocalDocumentStore) -> None:
    source = identity(b"original")
    with pytest.raises(EvidenceError, match="^SOURCE_HASH_MISMATCH$"):
        store.preserve(source, b"normalized")
    with pytest.raises(EvidenceError, match="^SOURCE_UNAVAILABLE$"):
        store.read_verified(source)


@pytest.mark.parametrize(
    "data,code", [(b"", "EMPTY_SOURCE"), (b"x" * (MAX_SOURCE_BYTES + 1), "SOURCE_TOO_LARGE")]
)
def test_source_limits(store: LocalDocumentStore, data: bytes, code: str) -> None:
    with pytest.raises(EvidenceError, match=f"^{code}$"):
        store.preserve(identity(data), data)


def test_concurrent_preservation_is_idempotent(store: LocalDocumentStore, tmp_path: Path) -> None:
    data = b"immutable policy"
    source = identity(data)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(lambda _: store.preserve(source, data), range(24)))
    assert store.read_verified(source) == data
    assert [p.name for p in (tmp_path / "private").iterdir()] == [source.object_key]


def test_tenant_key_separation(store: LocalDocumentStore) -> None:
    source = identity(b"A")
    store.preserve(source, b"A")
    other = replace(source, institution_id=uuid4())
    assert other.object_key != source.object_key
    with pytest.raises(EvidenceError, match="^SOURCE_UNAVAILABLE$"):
        store.read_verified(other)


def test_tampering_fails_reads_and_retries(store: LocalDocumentStore, tmp_path: Path) -> None:
    source = identity(b"original")
    store.preserve(source, b"original")
    path = tmp_path / "private" / source.object_key
    path.chmod(0o600)
    path.write_bytes(b"tampered")
    with pytest.raises(EvidenceError, match="^SOURCE_HASH_MISMATCH$"):
        store.read_verified(source)
    with pytest.raises(EvidenceError, match="^SOURCE_HASH_MISMATCH$"):
        store.preserve(source, b"original")
    assert path.read_bytes() == b"tampered", "Never silently repair/overwrite original storage"


def test_symlink_source_is_not_followed(store: LocalDocumentStore, tmp_path: Path) -> None:
    source = identity(b"outside")
    outside = tmp_path / "outside"
    outside.write_bytes(b"outside")
    (tmp_path / "private" / source.object_key).symlink_to(outside)
    with pytest.raises(EvidenceError, match="^SOURCE_STORAGE_UNAVAILABLE$"):
        store.read_verified(source)


def test_world_readable_storage_rejected(tmp_path: Path) -> None:
    root = tmp_path / "public"
    root.mkdir(mode=0o755)
    root.chmod(0o755)
    with pytest.raises(EvidenceError, match="^UNSAFE_STORAGE_PERMISSIONS$"):
        LocalDocumentStore(root)


@pytest.mark.parametrize("bad_hash", ["../escape", "A" * 64, "a" * 63, "a" * 64 + "\n"])
def test_invalid_source_keys_rejected(bad_hash: str) -> None:
    with pytest.raises(EvidenceError, match="^INVALID_HASH$"):
        SourceIdentity(uuid4(), uuid4(), bad_hash)


@pytest.mark.parametrize("current", list(BindingState))
@pytest.mark.parametrize("target", list(BindingState))
def test_binding_transitions(current: BindingState, target: BindingState) -> None:
    if (current, target) in {
        (BindingState.PROPOSED, BindingState.APPROVED),
        (BindingState.APPROVED, BindingState.REVOKED),
    }:
        validate_binding_transition(current, target)
    else:
        with pytest.raises(EvidenceError, match="^INVALID_BINDING_TRANSITION$"):
            validate_binding_transition(current, target)


def test_chunk_hash_and_unicode_locator_are_reproducible() -> None:
    original = "Header\r\n₹5 LPA 🧑".encode()
    artifact = "Header\n₹5 LPA 🧑".encode()
    chunk = Chunk(sha256(original), sha256(artifact), 0, "₹5 LPA 🧑", 7, 15)
    chunk.verify_artifact(artifact)
    assert chunk.source_hash != chunk.normalized_artifact_hash
    assert chunk.chunk_hash == replace(chunk).chunk_hash
    assert chunk.chunk_hash != replace(chunk, section="New section").chunk_hash
    with pytest.raises(EvidenceError, match="^ARTIFACT_HASH_MISMATCH$"):
        chunk.verify_artifact(original)
    with pytest.raises(EvidenceError, match="^CHUNK_LOCATOR_MISMATCH$"):
        replace(chunk, end_offset=999).verify_artifact(artifact)
    with pytest.raises(EvidenceError, match="^CHUNK_LOCATOR_MISMATCH$"):
        replace(chunk, text="Invented policy").verify_artifact(artifact)


def space() -> EmbeddingSpace:
    return EmbeddingSpace("test-only", "fixture", 2, "fixture-v1", "cosine", "v1")


@pytest.mark.parametrize(
    "changes",
    [
        {"provider": "local"},
        {"model": "other"},
        {"dimensions": 3},
        {"tokenizer": "other"},
        {"distance_metric": "dot"},
        {"pipeline_version": "v2"},
    ],
)
def test_space_identity_includes_all_provenance(changes: dict[str, object]) -> None:
    assert replace(space(), **changes).space_id != space().space_id


@pytest.mark.parametrize(
    "vectors,code",
    [
        ([], "EMBEDDING_COUNT_MISMATCH"),
        ([[1.0]], "EMBEDDING_DIMENSION_MISMATCH"),
        ([[float("nan"), 1.0]], "INVALID_EMBEDDING_VALUE"),
        ([[float("inf"), 1.0]], "INVALID_EMBEDDING_VALUE"),
        ([[True, 1.0]], "INVALID_EMBEDDING_VALUE"),
        ([[0.0, 0.0]], "ZERO_COSINE_VECTOR"),
    ],
)
def test_invalid_vectors_rejected(vectors: list[list[float]], code: str) -> None:
    with pytest.raises(EvidenceError, match=f"^{code}$"):
        validate_vectors(space(), vectors, 1)


def test_valid_vectors() -> None:
    validate_vectors(space(), [[0.5, 0.25]], 1)


def test_manifest_requires_exact_ids_hashes_count_and_uniqueness() -> None:
    a = ManifestPoint(uuid4(), sha256(b"a"))
    b = ManifestPoint(uuid4(), sha256(b"b"))
    validate_manifest([a, b], [b, a])
    for actual in (
        [],
        [a],
        [a, a],
        [a, replace(b, chunk_hash=a.chunk_hash)],
        [a, replace(b, point_id=uuid4())],
    ):
        with pytest.raises(EvidenceError, match="^INDEX_MANIFEST_MISMATCH$"):
            validate_manifest([a, b], actual)
    with pytest.raises(EvidenceError, match="^INDEX_MANIFEST_MISMATCH$"):
        validate_manifest([], [])
