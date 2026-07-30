# POC: Probabilistic Data Structures

A runnable companion to **Probabilistic data structures**
(`04-building-blocks/11-probabilistic-data-structures`). Three sketches that
trade a little accuracy for a lot of memory — and, crucially, **merge**, which
is what makes them a distributed-systems tool rather than a party trick.

| Sketch | File | Answers | Merge rule |
| --- | --- | --- | --- |
| `BloomFilter` | [`domain/bloom.py`](domain/bloom.py) | "have I seen this?" (no false negatives) | bitwise OR |
| `HyperLogLog` | [`domain/hyperloglog.py`](domain/hyperloglog.py) | "how many distinct?" (~2% error, 16 KB) | per-register max |
| `CountMinSketch` | [`domain/count_min.py`](domain/count_min.py) | "how often does X occur?" (never under-counts) | elementwise sum |

## Run it

```bash
./run            # accuracy/memory + merge-across-shards demo
./run test       # mypy --strict + unit tests + demo
./run check      # mypy only
```

Uses [`uv`](https://docs.astral.sh/uv/); no Docker, no ports, standard library only.

## What the demo proves

- **Bloom:** 50k items in ~60 KB with **zero** false negatives and a false-positive
  rate that matches the ~1% you dialed in via `optimal_k`.
- **HyperLogLog:** counts **1,000,000** distinct visitors within ~2% using a flat
  **16 KB** — independent of cardinality.
- **Count-Min:** recovers heavy-hitter frequencies from a noisy stream, only ever
  over-counting (the min-across-rows guarantee).
- **Merge:** four shards each sketch a disjoint quarter of a 1.2M-event stream;
  merging the four gives the **same distinct-count and frequency** as a single
  sketch built over the whole stream.

## What is simulated vs. real

In production these sketches live on **separate machines**: each shard of a
pipeline (a Kafka consumer, a Flink task, a Redis node running `PFADD`) maintains
its own sketch over the data it happens to see, and a coordinator periodically
pulls and merges them — a few kilobytes over the wire instead of billions of raw
events. This POC **mimics the shards in one process**: `SHARDS = 4` local sketch
objects, each fed a disjoint slice of the stream, then merged in a loop.

What is **identical to production**: the sketches and their merge operators. A
Bloom union really is a bitwise OR; an HLL merge really is a per-register max; a
Count-Min merge really is elementwise addition. That algebraic mergeability — an
associative, commutative combine — is exactly why these structures survive being
spread across machines. Only the transport (a method call instead of a network
fetch) is faked; there is no serialization format or coordinator process here.

**Not included:** the t-digest (quantiles) from the lesson. It is mergeable on
the same principle, but a correct implementation is substantially larger; the
three sketches here already demonstrate the merge property end to end.
