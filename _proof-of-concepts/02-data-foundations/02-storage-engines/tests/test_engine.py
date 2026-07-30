"""Unit tests for the LSM engine, using the in-memory segment store.

    python tests/test_engine.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.engine import LsmEngine  # noqa: E402
from infra.memory_store import InMemorySegmentStore  # noqa: E402


def _engine(threshold: int = 3) -> LsmEngine:
    return LsmEngine(InMemorySegmentStore(), memtable_threshold=threshold)


def test_put_get() -> None:
    e = _engine()
    e.put("a", "1")
    assert e.get("a") == "1"


def test_missing_key() -> None:
    assert _engine().get("nope") is None


def test_overwrite_newest_wins() -> None:
    e = _engine(2)
    e.put("k", "old")
    e.put("x", "1")  # crosses threshold → flush
    e.put("k", "new")
    e.flush()
    assert e.get("k") == "new"


def test_delete_tombstone() -> None:
    e = _engine(2)
    e.put("k", "v")
    e.put("x", "1")
    e.flush()
    e.delete("k")
    e.flush()
    assert e.get("k") is None


def test_compaction_merges_and_drops() -> None:
    e = _engine(2)
    for i in range(6):
        e.put(f"k{i}", str(i))
    e.put("k0", "updated")
    e.delete("k1")
    e.flush()
    before = e.stats()["live_segments"]
    e.compact()
    assert before > 1
    assert e.stats()["live_segments"] == 1
    assert e.get("k0") == "updated"
    assert e.get("k1") is None
    assert e.get("k2") == "2"


def test_scan_sorted_without_tombstones() -> None:
    e = _engine(2)
    e.put("b", "2")
    e.put("a", "1")
    e.put("c", "3")
    e.delete("b")
    e.flush()
    assert [en.key for en in e.scan()] == ["a", "c"]


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"PASS  {len(fns)} lsm engine tests")
