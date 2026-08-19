"""Pure unit tests for the sync agent, against an in-memory fake file service.

    python tests/test_agent.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.chunker import Chunker  # noqa: E402
from agent.manifest_differ import ManifestDiffer  # noqa: E402
from agent.ports import FileService  # noqa: E402
from agent.sync_engine import SyncEngine  # noqa: E402


class FakeFileService(FileService):
    def __init__(self) -> None:
        self.chunks: dict[str, bytes] = {}
        self.manifests: dict[str, list[str]] = {}
        self.puts = 0

    def get_manifest(self, path):
        return list(self.manifests.get(path, []))

    def missing_chunks(self, hashes):
        return [h for h in hashes if h not in self.chunks]

    def put_chunk(self, chunk_hash, data):
        self.chunks[chunk_hash] = data
        self.puts += 1

    def get_chunk(self, chunk_hash):
        return self.chunks[chunk_hash]

    def commit_manifest(self, path, hashes):
        self.manifests[path] = list(hashes)


def test_chunk_roundtrip():
    data = b"the quick brown fox jumps over the lazy dog " * 5
    chunks = Chunker(chunk_size=16).chunk(data)
    assert b"".join(c.data for c in chunks) == data


def test_identical_content_same_hash():
    c = Chunker(16)
    assert [x.hash for x in c.chunk(b"hello world")] == [x.hash for x in c.chunk(b"hello world")]


def test_manifest_differ():
    d = ManifestDiffer()
    assert d.diff(["a", "b", "c"], ["a", "b"]) == ["c"]
    assert d.diff(["a", "b"], ["a", "b"]) == []


def test_push_pull_roundtrip():
    svc = FakeFileService()
    engine = SyncEngine(svc, Chunker(16))
    data = b"content-addressed storage is neat " * 4
    engine.push("f.txt", data)
    assert engine.pull("f.txt") == data


def test_delta_sync_uploads_only_changed():
    svc = FakeFileService()
    engine = SyncEngine(svc, Chunker(16))
    data = b"A" * 16 + b"B" * 16 + b"C" * 16
    first = engine.push("f", data)
    assert first.uploaded == 3
    edited = data[:32] + b"Z" * 16          # change only the last chunk
    second = engine.push("f", edited)
    assert second.changed == 1 and second.uploaded == 1
    assert engine.pull("f") == edited


def test_global_dedup_across_files():
    svc = FakeFileService()
    engine = SyncEngine(svc, Chunker(16))
    data = b"A" * 16 + b"B" * 16
    engine.push("f1", data)
    result = engine.push("f2", data)          # same content, different path
    assert result.uploaded == 0               # every chunk already stored


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"PASS  {len(fns)} agent tests")
