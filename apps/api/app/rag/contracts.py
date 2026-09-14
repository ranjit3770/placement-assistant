"""Provider-independent M6 integrity contracts.

These checks are necessary, not sufficient, for serving evidence. PostgreSQL
authorization and transactional publication must additionally be enforced by the
application service. No vector payload can supply that authority.
"""

import hashlib
import json
import math
import re
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID

MAX_SOURCE_BYTES = 10 * 1024 * 1024
HASH_PATTERN = re.compile(r"[0-9a-f]{64}")


class EvidenceError(ValueError):
    """Stable error code safe for transport; no content or filesystem details."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def validate_hash(value: str) -> None:
    if not HASH_PATTERN.fullmatch(value):
        raise EvidenceError("INVALID_HASH")


@dataclass(frozen=True)
class SourceIdentity:
    institution_id: UUID
    document_id: UUID
    source_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.institution_id, UUID) or not isinstance(self.document_id, UUID):
            raise EvidenceError("INVALID_SOURCE_IDENTITY")
        validate_hash(self.source_hash)

    @property
    def object_key(self) -> str:
        # Caller filenames and M4 simulated paths never participate in storage.
        return f"{self.institution_id.hex}-{self.document_id.hex}-{self.source_hash}"


def verify_source(identity: SourceIdentity, data: bytes) -> None:
    if not data:
        raise EvidenceError("EMPTY_SOURCE")
    if len(data) > MAX_SOURCE_BYTES:
        raise EvidenceError("SOURCE_TOO_LARGE")
    if sha256(data) != identity.source_hash:
        raise EvidenceError("SOURCE_HASH_MISMATCH")


class DocumentStore(Protocol):
    """Blocking private storage adapter; invoke outside an async event loop.

    Identity must come from a tenant-authorized PostgreSQL Document lookup, not
    request data. This adapter verifies bytes, not user authorization or MIME.
    """

    def preserve(self, identity: SourceIdentity, data: bytes) -> None: ...

    def read_verified(self, identity: SourceIdentity) -> bytes: ...


class BindingState(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REVOKED = "REVOKED"


def validate_binding_transition(current: BindingState, target: BindingState) -> None:
    if (current, target) not in {
        (BindingState.PROPOSED, BindingState.APPROVED),
        (BindingState.APPROVED, BindingState.REVOKED),
    }:
        raise EvidenceError("INVALID_BINDING_TRANSITION")


@dataclass(frozen=True)
class Chunk:
    source_hash: str
    normalized_artifact_hash: str
    ordinal: int
    text: str
    start_offset: int
    end_offset: int
    page: int | None = None
    section: str | None = None
    schema_version: int = 1

    def __post_init__(self) -> None:
        validate_hash(self.source_hash)
        validate_hash(self.normalized_artifact_hash)
        if (
            self.schema_version != 1
            or self.ordinal < 0
            or self.start_offset < 0
            or self.end_offset <= self.start_offset
            or not self.text
            or (self.page is not None and self.page < 1)
        ):
            raise EvidenceError("INVALID_CHUNK")

    @property
    def chunk_hash(self) -> str:
        return sha256(canonical_bytes(asdict(self)))

    def verify_artifact(self, artifact: bytes) -> None:
        if sha256(artifact) != self.normalized_artifact_hash:
            raise EvidenceError("ARTIFACT_HASH_MISMATCH")
        try:
            text = artifact.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            raise EvidenceError("INVALID_ARTIFACT_ENCODING") from None
        if self.end_offset > len(text) or text[self.start_offset : self.end_offset] != self.text:
            raise EvidenceError("CHUNK_LOCATOR_MISMATCH")


@dataclass(frozen=True)
class EmbeddingSpace:
    provider: str
    model: str
    dimensions: int
    tokenizer: str
    distance_metric: str
    pipeline_version: str

    def __post_init__(self) -> None:
        if (
            not all(
                v.strip()
                for v in (self.provider, self.model, self.tokenizer, self.pipeline_version)
            )
            or self.dimensions <= 0
            or self.distance_metric not in {"cosine", "dot", "euclidean"}
        ):
            raise EvidenceError("INVALID_EMBEDDING_SPACE")

    @property
    def space_id(self) -> str:
        return sha256(canonical_bytes(asdict(self)))


class EmbeddingProvider(Protocol):
    @property
    def space(self) -> EmbeddingSpace: ...

    async def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]: ...


def validate_vectors(
    space: EmbeddingSpace, vectors: Sequence[Sequence[float]], expected_count: int
) -> None:
    if expected_count <= 0 or len(vectors) != expected_count:
        raise EvidenceError("EMBEDDING_COUNT_MISMATCH")
    for vector in vectors:
        if len(vector) != space.dimensions:
            raise EvidenceError("EMBEDDING_DIMENSION_MISMATCH")
        if any(isinstance(v, bool) or not math.isfinite(v) for v in vector):
            raise EvidenceError("INVALID_EMBEDDING_VALUE")
        if space.distance_metric == "cosine" and not any(v != 0 for v in vector):
            raise EvidenceError("ZERO_COSINE_VECTOR")


@dataclass(frozen=True)
class ManifestPoint:
    point_id: UUID
    chunk_hash: str

    def __post_init__(self) -> None:
        validate_hash(self.chunk_hash)


def validate_manifest(expected: Sequence[ManifestPoint], actual: Sequence[ManifestPoint]) -> None:
    """Compare independently fetched point IDs/hashes, not a payload count alone.

    Does not publish anything. The worker must separately verify sources,
    artifacts, chunks and vectors before its guarded database publication.
    """
    if (
        not expected
        or len(expected) != len(actual)
        or len({p.point_id for p in expected}) != len(expected)
        or len({p.point_id for p in actual}) != len(actual)
        or set(expected) != set(actual)
    ):
        raise EvidenceError("INDEX_MANIFEST_MISMATCH")


@dataclass(frozen=True)
class CitationMetadata:
    document_id: UUID
    source_hash: str
    chunk_hash: str
    ordinal: int
    page: int | None
    section: str | None
    start_offset: int
    end_offset: int

    def __post_init__(self) -> None:
        validate_hash(self.source_hash)
        validate_hash(self.chunk_hash)


@dataclass(frozen=True)
class VerifiedEvidence:
    text: str
    citation: CitationMetadata
    score: float | None = None
