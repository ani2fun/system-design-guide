"""Demo — accuracy vs. memory for three sketches, then the property that makes
them a distributed-systems tool: sketches built on separate shards MERGE into
the exact same answer as one built over the whole stream.

Run: `./run demo`
"""

from __future__ import annotations

from domain.bloom import BloomFilter
from domain.count_min import CountMinSketch
from domain.hyperloglog import HyperLogLog

SHARDS = 4


def demo_bloom() -> None:
    print("== Bloom filter: membership at a tunable false-positive rate ==")
    n = 50_000
    m = n * 10  # ~10 bits/item
    k = BloomFilter.optimal_k(m, n)
    bf = BloomFilter(m, k)
    for i in range(n):
        bf.add(f"member:{i}")

    false_negatives = sum(f"member:{i}" not in bf for i in range(n))
    trials = 100_000
    false_positives = sum(f"absent:{i}" in bf for i in range(trials))
    print(f"  {n} items in {bf.bytes_used() // 1024} KB, k={k}")
    print(f"  false negatives : {false_negatives}  (always 0 — the guarantee)")
    print(f"  false positives : {false_positives / trials:.2%}  observed")


def demo_hyperloglog() -> None:
    print("\n== HyperLogLog: count distinct in a fixed 16 KB ==")
    hll = HyperLogLog(precision=14)
    true = 1_000_000
    for i in range(true):
        hll.add(f"visitor:{i}")
    est = hll.count()
    print(f"  true distinct   : {true}")
    print(f"  HLL estimate    : {est}  ({abs(est - true) / true:.2%} error) in "
          f"{hll.bytes_used() // 1024} KB")


def demo_count_min() -> None:
    print("\n== Count-Min sketch: heavy-hitter frequency ==")
    cms = CountMinSketch(width=2000, depth=5)
    truth = {"hot": 100_000, "warm": 5_000, "cold": 50}
    for item, freq in truth.items():
        cms.add(item, freq)
    for _ in range(200_000):  # background noise
        cms.add("noise")
    for item, freq in truth.items():
        est = cms.estimate(item)
        print(f"  {item:<5} true={freq:>7}  est={est:>7}  (over-count {est - freq})")


def demo_merge_across_shards() -> None:
    print(f"\n== Mergeable across {SHARDS} simulated shards ==")
    print("  Each shard sees a disjoint slice of the stream and builds its own")
    print("  sketch; a coordinator merges them. Merge == whole-stream sketch.")

    events = [f"user:{i % 300_000}" for i in range(1_200_000)]  # 300k distinct

    # Global reference sketches (one machine sees everything).
    global_hll = HyperLogLog(14)
    global_cms = CountMinSketch(2000, 5)
    for e in events:
        global_hll.add(e)
        global_cms.add(e)

    # Sharded: each shard builds a local sketch over its slice only.
    shard_hlls = [HyperLogLog(14) for _ in range(SHARDS)]
    shard_cms = [CountMinSketch(2000, 5) for _ in range(SHARDS)]
    for idx, e in enumerate(events):
        s = idx % SHARDS
        shard_hlls[s].add(e)
        shard_cms[s].add(e)

    merged_hll = HyperLogLog(14)
    merged_cms = CountMinSketch(2000, 5)
    for s in range(SHARDS):
        merged_hll.merge(shard_hlls[s])
        merged_cms.merge(shard_cms[s])

    print(f"  HLL  distinct : global={global_hll.count()}  merged={merged_hll.count()}")
    print(f"  CMS  freq(user:0) : global={global_cms.estimate('user:0')}  "
          f"merged={merged_cms.estimate('user:0')}  (identical — additive merge)")


if __name__ == "__main__":
    demo_bloom()
    demo_hyperloglog()
    demo_count_min()
    demo_merge_across_shards()
