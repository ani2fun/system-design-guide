# POC: Toy LSM Engine

A runnable, pure-Python **log-structured merge (LSM) engine** for the
`data-foundations/storage-engines` lesson — the write path, read path, and
compaction that back Cassandra, RocksDB, LevelDB, and friends, small enough to
read in one sitting.

No Docker, no external engines — it's an in-process key/value store that writes
real segment files to a temp directory so you can watch them accumulate and
compact.

| Piece | File | Role |
| --- | --- | --- |
| `Memtable` | [`domain/memtable.py`](domain/memtable.py) | in-memory write buffer, flushed on threshold |
| `SSTable` | [`domain/sstable.py`](domain/sstable.py) | immutable sorted segment + Bloom filter + sparse index |
| `BloomFilter` | [`domain/bloom.py`](domain/bloom.py) | read-path membership test (skip a segment on a miss) |
| `Compactor` | [`domain/compaction.py`](domain/compaction.py) | merge segments, keep newest, drop tombstones |
| `LsmEngine` | [`domain/engine.py`](domain/engine.py) | put / get / delete / scan / flush / compact |
| `SegmentStore` (port) | [`domain/ports.py`](domain/ports.py) | disk vs in-memory segment persistence |

## Run it

```bash
./run            # the demonstration (write path → overwrite → Bloom skip → delete → compaction → scan)
./run test       # mypy --strict + unit tests + demo
./run check      # mypy --strict only
```

A [`uv`](https://docs.astral.sh/uv/) project (no runtime deps — standard library
only; `mypy` is the one dev dependency). `uv sync --python 3.12` sets up the venv.

## What the demo shows

1. **Write path** — writes buffer in the memtable and flush to immutable
   segment files at a size threshold (watch the `segment-*.dat` files appear).
2. **Write amplification** — a repeatedly-overwritten key physically exists in
   many segments; a read returns the newest, but the old copies linger.
3. **Read miss via Bloom filter** — a `get` for an absent key is answered
   "definitely not here" by each segment's Bloom filter, without a scan.
4. **Delete = tombstone** — a delete writes a marker that shadows older values.
5. **Compaction** — merging all segments reclaims the space spent on overwrites
   and tombstones, collapsing many files into one.
6. **Scan** — a merged, sorted iteration over the live keys.

## Design notes (SOLID / DDD)

The one genuine I/O boundary — *where segments are persisted* — is the
`SegmentStore` **port** (`abc.ABC`). `DiskSegmentStore` writes files;
`InMemorySegmentStore` (used by the tests) keeps a list. `LsmEngine` depends only
on the port, so it's exercised without touching a disk. Everything is
`mypy --strict` clean.
