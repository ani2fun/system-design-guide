from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.corpus import CORPUS  # noqa: E402
from domain.cluster import SearchCluster  # noqa: E402
from domain.index import InvertedIndex  # noqa: E402
from domain.scoring import BM25, TfIdf  # noqa: E402
from domain.tokenizer import STOPWORDS, analyze  # noqa: E402

SHARDS = 4


def _single(scorer: BM25 | TfIdf) -> InvertedIndex:
    idx = InvertedIndex(scorer)
    for doc_id, text in CORPUS.items():
        idx.add(doc_id, analyze(text))
    return idx


def _cluster(scorer_factory: object) -> SearchCluster:
    shards = [InvertedIndex(BM25()) for _ in range(SHARDS)]
    for i, (doc_id, text) in enumerate(CORPUS.items()):
        shards[i % SHARDS].add(doc_id, analyze(text))
    return SearchCluster(shards)


def test_tokenizer_drops_stopwords() -> None:
    tokens = analyze("The cat is ON the Mat")
    assert "the" not in tokens and "is" not in tokens and "on" not in tokens
    assert tokens == ["cat", "mat"]
    assert "the" in STOPWORDS


def test_search_finds_relevant_doc_first() -> None:
    idx = _single(BM25())
    hits = idx.search(analyze("raft leader log"), k=3)
    assert hits[0][0] == "raft"  # the doc literally about Raft ranks first


def test_only_matching_docs_returned() -> None:
    idx = _single(BM25())
    hits = idx.search(analyze("bloom membership"), k=5)
    ids = {doc_id for doc_id, _ in hits}
    assert "bloom-filter" in ids
    assert "kafka" not in ids  # no query term appears in the kafka doc


def test_rarer_term_outweighs_common_term() -> None:
    # "node" is common across the corpus; "paxos" is rare — a doc with paxos
    # should beat a doc that only matches the common term.
    idx = _single(TfIdf())
    hits = dict(idx.search(analyze("paxos node"), k=12))
    assert hits["consensus"] > hits["load-balancing"]


def test_scatter_gather_with_global_stats_matches_single_index() -> None:
    single = _single(BM25())
    cluster = _cluster(BM25)
    for term in CORPUS:
        query = analyze(CORPUS[term])[:3]
        if not query:
            continue
        assert single.search(query, k=3) == cluster.search(query, k=3, use_global_stats=True)


def test_local_stats_scatter_gather_can_diverge() -> None:
    # Compared on ranked doc order (not raw scores): naive per-shard idf reorders
    # results on at least one query, where global stats never do.
    single = _single(BM25())
    cluster = _cluster(BM25)

    def order(hits: list[tuple[str, float]]) -> list[str]:
        return [doc_id for doc_id, _ in hits]

    reorders = 0
    for term in CORPUS:
        query = analyze(CORPUS[term])[:3]
        if not query:
            continue
        base = order(single.search(query, k=3))
        if base != order(cluster.search(query, k=3, use_global_stats=False)):
            reorders += 1
    assert reorders > 0


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"PASS  {len(fns)} search tests")
