from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from domain.bloom import BloomFilter  # noqa: E402
from domain.count_min import CountMinSketch  # noqa: E402
from domain.hyperloglog import HyperLogLog  # noqa: E402


def test_bloom_no_false_negatives() -> None:
    bf = BloomFilter(m_bits=100_000, k_hashes=7)
    for i in range(5_000):
        bf.add(f"x{i}")
    assert all(f"x{i}" in bf for i in range(5_000))


def test_bloom_false_positive_rate_is_bounded() -> None:
    n, m = 5_000, 50_000
    k = BloomFilter.optimal_k(m, n)
    bf = BloomFilter(m, k)
    for i in range(n):
        bf.add(f"in{i}")
    fp = sum(f"out{i}" in bf for i in range(20_000)) / 20_000
    assert fp < 0.05  # ~1% expected at 10 bits/item; generous bound


def test_bloom_merge_is_union() -> None:
    a, b = BloomFilter(50_000, 7), BloomFilter(50_000, 7)
    a.add("apple")
    b.add("banana")
    a.merge(b)
    assert "apple" in a and "banana" in a


def test_bloom_merge_shape_mismatch_raises() -> None:
    try:
        BloomFilter(1000, 3).merge(BloomFilter(2000, 3))
    except ValueError:
        return
    raise AssertionError("expected ValueError on shape mismatch")


def test_hll_estimates_within_a_few_percent() -> None:
    hll = HyperLogLog(14)
    true = 200_000
    for i in range(true):
        hll.add(f"d{i}")
    assert abs(hll.count() - true) / true < 0.03


def test_hll_small_cardinality_linear_counting() -> None:
    hll = HyperLogLog(14)
    for i in range(500):
        hll.add(f"s{i}")
    assert abs(hll.count() - 500) / 500 < 0.05


def test_hll_merge_matches_whole_stream() -> None:
    events = [f"u{i % 50_000}" for i in range(200_000)]
    whole = HyperLogLog(14)
    for e in events:
        whole.add(e)
    left, right = HyperLogLog(14), HyperLogLog(14)
    for idx, e in enumerate(events):
        (left if idx % 2 else right).add(e)
    left.merge(right)
    assert left.count() == whole.count()


def test_cms_never_underestimates() -> None:
    cms = CountMinSketch(1000, 4)
    cms.add("k", 42)
    for i in range(10_000):
        cms.add(f"noise{i}")
    assert cms.estimate("k") >= 42


def test_cms_merge_is_additive() -> None:
    a, b = CountMinSketch(1000, 4), CountMinSketch(1000, 4)
    a.add("k", 10)
    b.add("k", 32)
    a.merge(b)
    assert a.estimate("k") == 42


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"PASS  {len(fns)} sketch tests")
