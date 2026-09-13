"""Private local development store with atomic, immutable object creation.

The administrator owns the root directory. No untrusted process may write it.
An object left behind after a SQL rollback is an unreachable reconciliation
candidate, not authorized evidence. This module intentionally offers no deletion.
"""

import os
import stat
import tempfile
from pathlib import Path

from app.rag.contracts import (
    MAX_SOURCE_BYTES,
    EvidenceError,
    SourceIdentity,
    verify_source,
)


class LocalDocumentStore:
    def __init__(self, root: Path) -> None:
        # Deployment configuration only, never caller-controlled paths.
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if root.is_symlink() or not root.is_dir():
            raise EvidenceError("UNSAFE_STORAGE_ROOT")
        if root.stat().st_mode & 0o077:
            raise EvidenceError("UNSAFE_STORAGE_PERMISSIONS")
        self._root = root.resolve(strict=True)

    def preserve(self, identity: SourceIdentity, data: bytes) -> None:
        verify_source(identity, data)
        try:
            # Complete writes before linking; a reader never sees partial bytes.
            with tempfile.NamedTemporaryFile(dir=self._root, prefix=".upload-") as staging:
                staging.write(data)
                staging.flush()
                os.fsync(staging.fileno())
                os.fchmod(staging.fileno(), 0o400)
                try:
                    os.link(staging.name, self._root / identity.object_key)
                except FileExistsError:
                    # Idempotent retry; never overwrite an existing/corrupt object.
                    self.read_verified(identity)
                directory = os.open(self._root, os.O_RDONLY | os.O_DIRECTORY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
        except OSError:
            raise EvidenceError("SOURCE_STORAGE_UNAVAILABLE") from None

    def read_verified(self, identity: SourceIdentity) -> bytes:
        try:
            descriptor = os.open(
                self._root / identity.object_key,
                os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
            )
            with os.fdopen(descriptor, "rb") as source:
                if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                    raise EvidenceError("INVALID_SOURCE_OBJECT")
                data = source.read(MAX_SOURCE_BYTES + 1)
        except FileNotFoundError:
            raise EvidenceError("SOURCE_UNAVAILABLE") from None
        except OSError:
            raise EvidenceError("SOURCE_STORAGE_UNAVAILABLE") from None
        verify_source(identity, data)
        return data
