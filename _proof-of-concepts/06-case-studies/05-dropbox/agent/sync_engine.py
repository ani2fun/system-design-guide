"""SyncEngine — upload missing chunks, then commit the manifest (C4 code element).

The sync state machine: chunk + hash the file, ask what changed vs the remote
manifest, upload only the changed chunks the server doesn't already have, then
commit the new manifest — the single act that flips the new version visible.
Depends on the Chunker, the ManifestDiffer, and the FileService port.
"""

from __future__ import annotations

from agent.chunker import Chunker
from agent.manifest_differ import ManifestDiffer
from agent.model import SyncResult
from agent.ports import FileService


class SyncEngine:
    def __init__(
        self,
        service: FileService,
        chunker: Chunker | None = None,
        differ: ManifestDiffer | None = None,
    ) -> None:
        self._service = service
        self._chunker = chunker or Chunker()
        self._differ = differ or ManifestDiffer()

    def push(self, path: str, data: bytes) -> SyncResult:
        chunks = self._chunker.chunk(data)
        by_hash = {c.hash: c.data for c in chunks}
        local = [c.hash for c in chunks]

        remote = self._service.get_manifest(path)
        changed = self._differ.diff(local, remote)
        missing = self._service.missing_chunks(changed)  # content-addressed dedup

        for chunk_hash in missing:
            self._service.put_chunk(chunk_hash, by_hash[chunk_hash])
        self._service.commit_manifest(path, local)  # version visible now

        return SyncResult(chunks_total=len(local), changed=len(changed), uploaded=len(missing))

    def pull(self, path: str) -> bytes:
        return b"".join(self._service.get_chunk(h) for h in self._service.get_manifest(path))
