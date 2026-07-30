"""Runnable demonstration of the toy LSM engine — every LSM idea, made visible.

    python -m app.demo   (or ./run)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from domain.engine import LsmEngine
from infra.disk_store import DiskSegmentStore


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="lsm-"))
    store = DiskSegmentStore(tmp)
    lsm = LsmEngine(store, memtable_threshold=4)
    print(f"data dir: {tmp}\n")

    print("1) WRITE PATH — buffer in the memtable, flush to an immutable segment at threshold=4")
    for i in range(1, 11):
        lsm.put(f"key{i:02d}", f"v{i}")
    print(f"   wrote 10 keys → segment files on disk: {store.segment_files()}")
    print(f"   {lsm.stats()}\n")

    print("2) OVERWRITE = write amplification — a hot key rewritten lands in many segments")
    for version in ("a", "b", "c", "d", "e"):
        lsm.put("hot", version)
        lsm.flush()  # force each version into its own segment to make the point
    print(f"   'hot' read = {lsm.get('hot')!r} (newest wins), yet it physically exists in 5 segments")
    print(f"   total entries across segments = {lsm.stats()['total_segment_entries']}\n")

    print("3) READ MISS — a Bloom filter lets a segment answer 'definitely not here' without a scan")
    _ = lsm.get("no-such-key")
    print(f"   get('no-such-key') = {lsm.get('no-such-key')!r}; Bloom-skipped segment checks = {lsm.stats()['bloom_skips']}\n")

    print("4) DELETE — a tombstone shadows older values")
    lsm.delete("key01")
    lsm.flush()
    print(f"   get('key01') after delete = {lsm.get('key01')!r}\n")

    print("5) COMPACTION — merge all segments, reclaiming overwrites + tombstones")
    before = lsm.stats()
    lsm.compact()
    after = lsm.stats()
    print(f"   segments {before['live_segments']} → {after['live_segments']}; "
          f"entries {before['total_segment_entries']} → {after['total_segment_entries']} "
          f"(reclaimed {before['total_segment_entries'] - after['total_segment_entries']})")
    print(f"   files: {store.segment_files()}")
    print(f"   'hot' still = {lsm.get('hot')!r}; 'key01' still deleted = {lsm.get('key01')!r}\n")

    print("6) SCAN — sorted live keys after compaction")
    print("   " + ", ".join(f"{e.key}={e.value}" for e in lsm.scan()))
    print("\nPASS  toy LSM demo")


if __name__ == "__main__":
    main()
