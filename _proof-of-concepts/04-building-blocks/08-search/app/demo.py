"""Demo — build an inverted index, rank with BM25, then shard the corpus and show
that scatter-gather reproduces the single-index ranking *only* when the shards
score against global collection statistics.

Run: `./run demo`
"""

from __future__ import annotations

from app.corpus import CORPUS
from domain.cluster import SearchCluster
from domain.index import InvertedIndex
from domain.scoring import BM25
from domain.tokenizer import analyze

SHARDS = 4


def _print_hits(hits: list[tuple[str, float]]) -> None:
    for doc_id, score in hits:
        print(f"    {score:5.2f}  {doc_id}")


def build_single() -> InvertedIndex:
    idx = InvertedIndex(BM25())
    for doc_id, text in CORPUS.items():
        idx.add(doc_id, analyze(text))
    return idx


def build_shards() -> SearchCluster:
    shards = [InvertedIndex(BM25()) for _ in range(SHARDS)]
    for i, (doc_id, text) in enumerate(CORPUS.items()):
        shards[i % SHARDS].add(doc_id, analyze(text))
    return SearchCluster(shards)


def main() -> None:
    single = build_single()
    cluster = build_shards()

    for query_text in ("distributed consensus log", "cache data", "index term documents"):
        query = analyze(query_text)
        print(f'== query: "{query_text}"  → terms {query} ==')
        print("  single global index (BM25):")
        _print_hits(single.search(query, k=3))
        print(f"  scatter-gather over {SHARDS} shards, GLOBAL stats:")
        _print_hits(cluster.search(query, k=3, use_global_stats=True))
        print(f"  scatter-gather over {SHARDS} shards, LOCAL stats (naive, wrong):")
        _print_hits(cluster.search(query, k=3, use_global_stats=False))
        print()

    # Quantify agreement of the ranked doc order (ignoring absolute scores).
    def order(hits: list[tuple[str, float]]) -> list[str]:
        return [doc_id for doc_id, _ in hits]

    agree_global = agree_local = total = 0
    for term in CORPUS:
        query = analyze(CORPUS[term])[:3]
        if not query:
            continue
        total += 1
        base = order(single.search(query, k=3))
        if base == order(cluster.search(query, k=3, use_global_stats=True)):
            agree_global += 1
        if base == order(cluster.search(query, k=3, use_global_stats=False)):
            agree_local += 1
    print(f"Top-3 ranking agreement with the single index over {total} queries:")
    print(f"  global-stats scatter-gather : {agree_global}/{total}  (exact — same idf everywhere)")
    print(f"  local-stats  scatter-gather : {agree_local}/{total}  (drifts — each shard's idf differs)")


if __name__ == "__main__":
    main()
