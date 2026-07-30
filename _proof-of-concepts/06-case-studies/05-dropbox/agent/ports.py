"""Port — the file service, as the sync agent sees it (Dependency Inversion).

Explicit `abc.ABC`: the HTTP adapter talks to the real service; a fake could
implement it in tests. The agent never imports urllib or knows a URL.
"""

from __future__ import annotations

import abc


class FileService(abc.ABC):
    @abc.abstractmethod
    def get_manifest(self, path: str) -> list[str]:
        """The committed chunk-hash list for a path ([] if new)."""

    @abc.abstractmethod
    def missing_chunks(self, hashes: list[str]) -> list[str]:
        """Of the given hashes, those NOT already stored (content-addressed dedup)."""

    @abc.abstractmethod
    def put_chunk(self, chunk_hash: str, data: bytes) -> None: ...

    @abc.abstractmethod
    def get_chunk(self, chunk_hash: str) -> bytes: ...

    @abc.abstractmethod
    def commit_manifest(self, path: str, hashes: list[str]) -> None:
        """Make a new version visible atomically."""
