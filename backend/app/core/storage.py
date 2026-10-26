"""File storage. Bytes are saved once under their SHA-256 and never overwritten.

Goes through fsspec, so moving from the local folder to MinIO/S3 later means changing
AP_STORAGE_ROOT (e.g. "s3://bucket/automation") and nothing else.
"""

import hashlib
from pathlib import Path

import fsspec

from app.config import get_settings


class Storage:
    def __init__(self, root: str):
        self.fs, self.root = fsspec.core.url_to_fs(root)
        self.fs.makedirs(self.root, exist_ok=True)

    def _path(self, sha256: str) -> str:
        return f"{self.root}/{sha256[:2]}/{sha256}"

    def put(self, data: bytes) -> str:
        """Save bytes and return their SHA-256. Saving the same bytes twice keeps one copy."""
        sha = hashlib.sha256(data).hexdigest()
        path = self._path(sha)
        if not self.fs.exists(path):
            self.fs.makedirs(path.rsplit("/", 1)[0], exist_ok=True)
            with self.fs.open(path, "wb") as f:
                f.write(data)
        return sha

    def get(self, sha256: str) -> bytes:
        with self.fs.open(self._path(sha256), "rb") as f:
            return f.read()

    def local_path(self, sha256: str) -> Path:
        """A path on local disk, for libraries that need a real file. Local storage only."""
        return Path(self._path(sha256))


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        _storage = Storage(get_settings().storage_root)
    return _storage
